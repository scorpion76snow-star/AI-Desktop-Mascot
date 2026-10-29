# -*- coding: utf-8 -*-
"""Small runtime i18n layer for the UI.

The source keeps Chinese labels; this module translates widget text for the
selected language. Dynamic status lines get a few regex translations too.
"""

import re

from PySide6.QtWidgets import (
    QLabel, QPushButton, QCheckBox, QRadioButton, QGroupBox, QLineEdit,
    QComboBox, QTabWidget, QDialog, QMainWindow,
)

ZH_EN = {
    "打开工作台": "Open workspace",
    "聊天": "Chat",
    "显示/隐藏桌宠": "Show/Hide pet",
    "声音提示": "Voice",
    "退出": "Quit",
    "小云桌宠": "Yun Pet",
    "日历": "Calendar",
    "待办": "To-do",
    "记事本": "Notes",
    "待发送": "Pending",
    "设置": "Settings",
    "选中日期的日程": "Events for the selected day",
    "新建": "New",
    "编辑": "Edit",
    "删除": "Delete",
    "完成/取消": "Done/Undo",
    "标题": "Title",
    "开始": "Start",
    "结束": "End",
    "地点": "Place",
    "备注": "Note",
    "截止": "Due",
    "优先级": "Priority",
    "高": "High",
    "中": "Medium",
    "低": "Low",
    "保存": "Save",
    "刷新": "Refresh",
    "打开": "Open",
    "关闭": "Close",
    "语言切换按钮在窗口右上角，切换后应用会重启。": "Language button is at the top right; the app restarts after switching.",
    "保存模型": "Save model",
    "测试/加载": "Test / Load",
    "当前模型": "Active model",
    "OpenAI 模型": "OpenAI model",
    "打开皮肤目录": "Open skin folder",
    "打开语音目录": "Open voice folder",
    "应用名称": "App name",
    "接口地址": "Base URL",
    "皮肤": "Skin",
    "界面/形象": "UI / Pet",
    "把 pet.png / style.qss 放到 %APPDATA%\\YunPet\\skins\\<皮肤名>\\": "Put pet.png / style.qss in %APPDATA%\\YunPet\\skins\\<skin>\\",
    "API key（存入 Windows Credential Manager）": "API key (stored in Windows Credential Manager)",
    "删除选中": "Delete selected",
    "清空全部": "Clear all",
    "历史": "History",
    "新对话": "New chat",
    "朗读": "Read aloud",
    "发送": "Send",
    "聊天记录": "Chat history",
    "聊天自动朗读": "Read chat replies",
    "邮件提醒朗读": "Read mail alerts",
    "桌宠待办朗读": "Read pet to-do",
    "开启声音提示": "Enable voice",
    "当前引擎": "Voice engine",
    "音量": "Volume",
    "勿扰时段": "Quiet hours",
    "试听中文": "Test Chinese",
    "试听英文": "Test English",
    "语音提醒": "Voice",
    "模型": "Model",
    "加载模型": "Load model",
    "邮件": "Mail",
    "邮件接口": "Mail provider",
    "服务商": "Provider",
    "账号备注": "Account label",
    "客户端 ID": "Client ID",
    "邮件账号（可多个）": "Mail accounts (multiple)",
    "添加账号": "Add account",
    "新增": "Add",
    "保存账号": "Save account",
    "测试连接": "Test connection",
    "允许发送": "Allow sending",
    "已批准": "Approved",
    "发送失败": "Send failed",
    "无标题": "Untitled",
    "未启用": "Disabled",
    "和小云说点什么…": "Say something to Yun…",
    "账号备注，如 work": "Account label, e.g. work",
    "例如 23:00-07:00，留空表示不启用": "e.g. 23:00-07:00; leave blank to disable",
    "待发送草稿：只有你点“允许发送”才会交给邮件接口": "Pending drafts: they are sent only after you allow them.",
    "选择一次对话打开；删除只影响聊天记录，不影响邮件/日历/待办。": "Open a conversation. Deleting only affects chat history.",
    "编辑日程": "Edit event",
    "新建日程": "New event",
    "编辑待办": "Edit to-do",
    "新建待办": "New to-do",
    "确定删除这个日程？": "Delete this event?",
    "确定删除这个待办？": "Delete this to-do?",
    "确定删除这条笔记？": "Delete this note?",
    "确定删除这次对话？": "Delete this conversation?",
    "确定删除全部聊天记录？此操作不可恢复。": "Delete all chat history? This cannot be undone.",
    "老板": "Boss",
    "小云": "Yun",
    "我在这儿，老板。": "I'm here, Boss.",
    "新对话开始了，老板。": "New conversation started, Boss.",
    "上下文：0 轮": "Context: 0 turns",
}

EN_ZH = {v: k for k, v in ZH_EN.items()}
EN_ZH.update({"Chat": "聊天", "Boss": "老板", "Yun": "小云",
              "App name": "应用名称", "Base URL": "接口地址",
              "OpenAI model": "OpenAI 模型", "Save model": "保存模型",
              "Test / Load": "测试/加载", "Active model": "当前模型",
              "Skin": "皮肤", "UI / Pet": "界面/形象",
              "Open skin folder": "打开皮肤目录", "Open voice folder": "打开语音目录"})


def tr_text(text, lang="en"):
    if not text:
        return text
    table = ZH_EN if lang == "en" else EN_ZH
    if text in table:
        return table[text]
    # dynamic status lines
    if lang == "en":
        m = re.match(r"上下文：(\d+) 轮(?:（省略 (\d+) 轮）)?(?: \+ 摘要)? · (?:约 )?(\d+) tokens", text)
        if m:
            extra = f" (omitted {m.group(2)})" if m.group(2) else ""
            return f"Context: {m.group(1)} turns{extra} · {m.group(3)} tokens"
        m = re.match(r"上下文：(\d+) 轮 · 新对话可用", text)
        if m:
            return f"Context: {m.group(1)} turns · new chat"
        m = re.match(r"模型：(.+?)(?: · 已拦截低质量回复)?$", text, re.S)
        if m:
            suffix = " · low-quality reply blocked" if "已拦截" in text else ""
            return f"Model: {m.group(1)}{suffix}"
        if text.startswith("上下文："):
            return text.replace("上下文：", "Context: ").replace("（省略 ", " (omitted ").replace(" 轮）", " turns)")
    else:
        if text.startswith("Context: "):
            return text.replace("Context: ", "上下文：").replace(" turns", " 轮")
    return text


def translate_tree(root, lang="en"):
    if root is None or lang != "en":
        return
    for w in root.findChildren(QLabel):
        w.setText(tr_text(w.text(), lang))
    for w in root.findChildren(QPushButton):
        w.setText(tr_text(w.text(), lang))
    for w in root.findChildren(QCheckBox):
        w.setText(tr_text(w.text(), lang))
    for w in root.findChildren(QRadioButton):
        w.setText(tr_text(w.text(), lang))
    for w in root.findChildren(QGroupBox):
        w.setTitle(tr_text(w.title(), lang))
    for w in root.findChildren(QLineEdit):
        if w.placeholderText():
            w.setPlaceholderText(tr_text(w.placeholderText(), lang))
    for w in root.findChildren(QComboBox):
        for i in range(w.count()):
            w.setItemText(i, tr_text(w.itemText(i), lang))
    for w in root.findChildren(QTabWidget):
        for i in range(w.count()):
            w.setTabText(i, tr_text(w.tabText(i), lang))
    title = getattr(root, "windowTitle", lambda: "")()
    if title:
        root.setWindowTitle(tr_text(title, lang))
    for w in root.findChildren(QDialog):
        title = w.windowTitle()
        if title:
            w.setWindowTitle(tr_text(title, lang))
