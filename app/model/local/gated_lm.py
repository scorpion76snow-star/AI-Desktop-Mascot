import math
from dataclasses import dataclass
import torch, torch.nn as nn, torch.nn.functional as F

REPLY, ESCALATE, IGNORE = 0, 1, 2


@dataclass
class Cfg:
    vocab: int = 16384
    d: int = 576
    n_layer: int = 10
    n_head: int = 9         
    n_kv: int = 3           
    ffn_mult: float = 3.0
    max_len: int = 1024
    rope_base: float = 10000.0
    gate_hidden: int = 64
    n_gate: int = 3


class RMSNorm(nn.Module):
    def __init__(s, d, eps=1e-6):
        super().__init__(); s.w = nn.Parameter(torch.ones(d)); s.eps = eps
    def forward(s, x):
        return x * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + s.eps).to(x.dtype) * s.w


def rope(x, cos, sin):  # x: B,H,T,D
    x1, x2 = x.chunk(2, -1)
    return torch.cat([x1 * cos - x2 * sin, x2 * cos + x1 * sin], -1)


class Attn(nn.Module):
    def __init__(s, c: Cfg):
        super().__init__()
        s.nh, s.nkv, s.hd = c.n_head, c.n_kv, c.d // c.n_head
        assert c.n_head % c.n_kv == 0
        s.q = nn.Linear(c.d, s.nh * s.hd, bias=False)
        s.kv = nn.Linear(c.d, 2 * s.nkv * s.hd, bias=False)
        s.o = nn.Linear(s.nh * s.hd, c.d, bias=False)
    def forward(s, x, cos, sin):
        B, T, _ = x.shape
        q = s.q(x).view(B, T, s.nh, s.hd).transpose(1, 2)
        k, v = s.kv(x).view(B, T, 2, s.nkv, s.hd).permute(2, 0, 3, 1, 4)
        q, k = rope(q, cos, sin), rope(k, cos, sin)
        r = s.nh // s.nkv
        k, v = k.repeat_interleave(r, 1), v.repeat_interleave(r, 1)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return s.o(y.transpose(1, 2).reshape(B, T, -1))


class FFN(nn.Module): 
    def __init__(s, c: Cfg):
        super().__init__()
        h = int(c.d * c.ffn_mult) // 64 * 64
        s.g = nn.Linear(c.d, h, bias=False); s.u = nn.Linear(c.d, h, bias=False)
        s.dn = nn.Linear(h, c.d, bias=False)
    def forward(s, x): return s.dn(F.silu(s.g(x)) * s.u(x))


class Block(nn.Module):
    def __init__(s, c: Cfg):
        super().__init__()
        s.n1, s.n2 = RMSNorm(c.d), RMSNorm(c.d)
        s.attn, s.ffn = Attn(c), FFN(c)
    def forward(s, x, cos, sin):
        x = x + s.attn(s.n1(x), cos, sin)
        return x + s.ffn(s.n2(x))


class GateHead(nn.Module):
    def __init__(s, c: Cfg):
        super().__init__()
        s.net = nn.Sequential(nn.Linear(c.d, c.gate_hidden, bias=False), nn.SiLU(),
                              nn.Linear(c.gate_hidden, c.n_gate, bias=False))
    def forward(s, h): return s.net(h)


class GatedLM(nn.Module):
    def __init__(s, c: Cfg):
        super().__init__()
        s.c = c
        s.emb = nn.Embedding(c.vocab, c.d)
        s.blocks = nn.ModuleList(Block(c) for _ in range(c.n_layer))
        s.norm = RMSNorm(c.d)
        s.lm_head = nn.Linear(c.d, c.vocab, bias=False)
        s.lm_head.weight = s.emb.weight           
        s.gate = GateHead(c)
        hd = c.d // c.n_head
        f = 1.0 / (c.rope_base ** (torch.arange(0, hd, 2).float() / hd))
        a = torch.outer(torch.arange(c.max_len).float(), f)
        s.register_buffer("cos", a.cos()[None, None], persistent=False)
        s.register_buffer("sin", a.sin()[None, None], persistent=False)
        s.apply(s._init)
        for b in s.blocks:                        
            for m in (b.attn.o, b.ffn.dn):
                nn.init.normal_(m.weight, 0, 0.02 / math.sqrt(2 * c.n_layer))

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, 0, 0.02)

    def trunk(s, idx):
        T = idx.shape[1]
        x = s.emb(idx)
        cos, sin = s.cos[:, :, :T].to(x.dtype), s.sin[:, :, :T].to(x.dtype)
        for b in s.blocks:
            x = b(x, cos, sin)
        return s.norm(x)

    def forward(s, idx, gate_pos, targets=None, gate_labels=None,
                lam=0.3, detach_gate=True, gate_w=None):
        x = s.trunk(idx)
        h = x[torch.arange(idx.shape[0], device=idx.device), gate_pos]
        g_logits = s.gate(h.detach() if detach_gate else h)
        out = {"gate_logits": g_logits}
        if targets is not None:
            lm = F.cross_entropy(s.lm_head(x).flatten(0, 1).float(), targets.flatten(), ignore_index=-100)
            out["lm_loss"] = lm
        if gate_labels is not None:
            gl = F.cross_entropy(g_logits.float(), gate_labels, weight=gate_w)
            out["gate_loss"] = gl
            if targets is not None:
                out["loss"] = lm + lam * gl
        return out

    @torch.no_grad()
    def decide(s, prompt_ids, tau_reply=0.9, tau_ignore=0.9, temperature=1.0):
        x = s.trunk(prompt_ids)
        p = F.softmax(s.gate(x[:, -1]).float() / temperature, -1)[0]
        if p[REPLY] >= tau_reply:   return REPLY, p
        if p[IGNORE] >= tau_ignore: return IGNORE, p
        return ESCALATE, p


def fit_temperature(logits, labels, iters=50):
    t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([t], lr=0.1, max_iter=iters)
    def closure():
        opt.zero_grad(); l = F.cross_entropy(logits / t.exp(), labels); l.backward(); return l
    opt.step(closure)
    return t.exp().item()


if __name__ == "__main__":
    c = Cfg()
    m = GatedLM(c)
    n = sum(p.numel() for p in m.parameters())
    print(f"params {n/1e6:.2f}M | embedding {c.vocab*c.d/1e6:.2f}M | gate {sum(p.numel() for p in m.gate.parameters())/1e3:.1f}K")
    B, T = 4, 64
    idx = torch.randint(0, c.vocab, (B, T))
    tg = idx.clone(); tg[:, :32] = -100; tg[0] = -100        
    o = m(idx, torch.full((B,), 31), tg, torch.tensor([1, 0, 0, 2]))
    o["loss"].backward()
    print({k: round(v.item(), 3) for k, v in o.items() if v.ndim == 0})
    print(m.decide(idx[:1, :32]))
