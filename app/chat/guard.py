# -*- coding: utf-8 -*-
"""部署侧的安全兜底：钱/合同/法律/医疗/紧急/PII/看图 -> 转人工；
促销/订阅/验证码/群发 -> 忽略。

模型的 gate head 是在 3,000 条上学的，遇到训练分布外的说法会漏判；
这层规则只负责“宁可转人工，也不自动回”，不参与训练，也不改变模型。

    from app.chat.guard import classify
    classify("帮我把五千块转给这个账户")  # -> 1 (ESCALATE)
    classify("【限时特惠】秋季外套五折")    # -> 2 (IGNORE)
    classify("你吃了吗")                    # -> None
"""

import re

REPLY, ESCALATE, IGNORE = 0, 1, 2

ESCALATE_PATTERNS = [
    # 钱 / 支付 / 账户
    r"(转账|汇款|打款|付款|支付|退款|报销|发票|银行卡|账户|余额|工资|奖金|押金|定金|尾款)",
    r"(转|汇|打|付|退|借|还).{0,6}(钱|款|账|费|元|块|万|千|百)",
    # 合同 / 法律
    r"(合同|协议|条款|签约|盖章|律师|起诉|诉讼|仲裁|赔偿|违约|法务)",
    # 医疗
    r"(头疼|头痛|发烧|发热|胸痛|肚子疼|过敏|吃药|处方|医院|医生|急救|晕倒|受伤|手术|诊断)",
    # 紧急
    r"(着火|火灾|报警|警察|车祸|事故|有人受伤|进小偷|被盗)",
    # 陌生人套老板信息
    r"(老板|他|她)的(手机号|电话|住址|家庭地址|身份证|护照|密码|行程|行踪)",
    r"(把|给|发).{0,6}(老板|他|她).{0,6}(手机号|电话|住址|地址|身份证|护照|密码)",
    r"(手机号|身份证号|护照号|密码).{0,6}(给我|发我|多少|告诉我)",
    # 看图 / 附件
    r"(看图|这张图|图片|照片|截图|扫描件|附件|image|photo|screenshot|picture)",
]

IGNORE_PATTERNS = [
    r"(促销|特惠|折扣|五折|秒杀|清仓|优惠|满减|限时|领券|包邮|sale|discount|promo|clearance|coupon)",
    r"(订阅|续费|会员到期|自动续费|subscription|renew)",
    r"(验证码|校验码|动态码|verification code|otp|code is)",
    r"(群发|全员|各位同事|通知全体|announcement|all staff|dear all)",
]

_ESC = re.compile("|".join(ESCALATE_PATTERNS), re.I)
_IGN = re.compile("|".join(IGNORE_PATTERNS), re.I)


def classify(text: str):
    """Return 1, 2, or None.  ESCALATE wins over IGNORE."""
    if not text:
        return None
    if _ESC.search(text):
        return ESCALATE
    if _IGN.search(text):
        return IGNORE
    return None
