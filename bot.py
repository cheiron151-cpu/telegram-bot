import os
import json
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

# Khởi tạo các client
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def load_quan_an():
    with open("quan_an.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["quan_an"]


def save_quan_an(danh_sach):
    with open("quan_an.json", "w", encoding="utf-8") as f:
        json.dump({"quan_an": danh_sach}, f, ensure_ascii=False, indent=2)


def search_va_tom_tat(chu_de: str) -> str:
    # Tìm kiếm xu hướng qua Tavily
    ket_qua = tavily.search(
        query=chu_de,
        search_depth="advanced",
        max_results=8
    )

    # Gom nội dung tìm được
    noi_dung = "\n".join([r["content"] for r in ket_qua["results"]])

    # Dùng Claude tóm tắt
    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Dựa vào thông tin sau, hãy tóm tắt ngắn gọn top xu hướng {chu_de} hiện nay bằng tiếng Việt.
Trình bày rõ ràng, dùng emoji cho sinh động, tối đa 5 mục.

Thông tin:
{noi_dung}"""
        }]
    )
    return response.content[0].text


# === Các lệnh bot ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Xin chào! Tôi là bot xu hướng & ăn uống.\n\n"
        "📌 Các lệnh:\n"
        "/nhac — Xu hướng âm nhạc\n"
        "/phim — Xu hướng phim\n"
        "/game — Xu hướng game\n"
        "/angi — Bốc thăm chỗ ăn\n"
        "/themquan [tên quán] — Thêm quán vào danh sách\n"
        "/xoaquan [số thứ tự] — Xóa quán (vd: /xoaquan 2 hoặc /xoaquan 1 3 5)\n"
        "/danhsach — Xem danh sách quán"
    )


async def xu_huong_nhac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Đang tìm xu hướng âm nhạc...")
    now = datetime.now()
    ket_qua = search_va_tom_tat(
        f"top bài hát trending Việt Nam tháng {now.month} năm {now.year} kenh14 znews baomoi "
        f"nhạc Việt hot nhất tuần bảng xếp hạng âm nhạc {now.year}"
    )
    await update.message.reply_text(ket_qua)


async def xu_huong_phim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Đang tìm xu hướng phim...")
    now = datetime.now()
    ket_qua = search_va_tom_tat(
        f"phim đang chiếu rạp Việt Nam tháng {now.month} {now.year} CGV Lotte Cinema doanh thu cao nhất "
        f"phim Netflix VieON FPT Play mới nhất đang hot tuần này {now.year}"
    )
    await update.message.reply_text(ket_qua)


async def xu_huong_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 Đang tìm xu hướng game...")
    now = datetime.now()
    ket_qua = search_va_tom_tat(
        f"Steam best sellers top games {now.year} most played this week "
        f"game hot nhất đang được bàn luận IGN GameSpot PC Gamer {now.year}"
    )
    await update.message.reply_text(ket_qua)


async def an_gi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    danh_sach = load_quan_an()
    if not danh_sach:
        await update.message.reply_text("Danh sách quán trống! Thêm quán bằng /themquan")
        return
    chon = random.choice(danh_sach)
    await update.message.reply_text(f"🍽️ Hôm nay ăn:\n\n**{chon}**", parse_mode="Markdown")


async def them_quan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Dùng: /themquan Tên quán ăn")
        return
    ten_quan = " ".join(context.args)
    danh_sach = load_quan_an()
    danh_sach.append(ten_quan)
    save_quan_an(danh_sach)
    await update.message.reply_text(f"✅ Đã thêm: {ten_quan}")


async def xoa_quan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Dùng: /xoaquan [số thứ tự]\nVí dụ: /xoaquan 2\nHoặc xóa nhiều: /xoaquan 1 3 5\nXem số thứ tự bằng /danhsach")
        return

    danh_sach = load_quan_an()
    try:
        # Lấy các số thứ tự, chuyển sang index (trừ 1), sắp xếp ngược để xóa từ cuối
        indices = sorted(set(int(x) - 1 for x in context.args), reverse=True)

        # Kiểm tra index hợp lệ
        for i in indices:
            if i < 0 or i >= len(danh_sach):
                await update.message.reply_text(f"❌ Số {i+1} không tồn tại trong danh sách.")
                return

        da_xoa = [danh_sach[i] for i in sorted(indices)]
        for i in indices:
            danh_sach.pop(i)

        save_quan_an(danh_sach)
        ten_da_xoa = "\n".join(f"- {q}" for q in da_xoa)
        await update.message.reply_text(f"🗑️ Đã xóa:\n{ten_da_xoa}\n\nCòn lại {len(danh_sach)} quán.")
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số thứ tự hợp lệ. Ví dụ: /xoaquan 2 4")


async def xem_danh_sach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    danh_sach = load_quan_an()
    if not danh_sach:
        await update.message.reply_text("Danh sách trống!")
        return
    text = "🍜 Danh sách quán ăn:\n\n"
    for i, quan in enumerate(danh_sach, 1):
        text += f"{i}. {quan}\n"
    await update.message.reply_text(text)


# === Chạy bot ===
if __name__ == "__main__":
    # Fix cho Windows Python 3.12+ (chỉ áp dụng trên Windows)
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nhac", xu_huong_nhac))
    app.add_handler(CommandHandler("phim", xu_huong_phim))
    app.add_handler(CommandHandler("game", xu_huong_game))
    app.add_handler(CommandHandler("angi", an_gi))
    app.add_handler(CommandHandler("themquan", them_quan))
    app.add_handler(CommandHandler("xoaquan", xoa_quan))
    app.add_handler(CommandHandler("danhsach", xem_danh_sach))

    print("Bot dang chay...")
    app.run_polling()

