import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN
from game import UnoGame, Color

logging.basicConfig(level=logging.INFO)
games = {}
waiting = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привіт! Напиши /join для гри в UNO.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id; uid = update.effective_user.id
    waiting.setdefault(cid, set()).add(uid)
    await update.message.reply_text(f"{update.effective_user.first_name} приєднався. Гравців: {len(waiting[cid])}")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    players = list(waiting.get(cid, []))
    if len(players) < 2:
        await update.message.reply_text("Потрібно мінімум 2 гравці.")
        return
    waiting.pop(cid, None)
    game = UnoGame(players); game.deal(); games[cid] = game
    for pid in players:
        await context.bot.send_message(pid, "🎴 Твої карти:\n" + "\n".join(str(c) for c in game.hands[pid]))
    await context.bot.send_message(cid, f"Гра розпочалась! Карта на столі: {game.discard[-1]}")
    await prompt_move(context, cid)

async def prompt_move(ctx, cid):
    game = games[cid]; pid = game.current_player()
    hand = game.hands[pid]; top = game.discard[-1]
    btns = [[InlineKeyboardButton(str(c), callback_data=f"play:{cid}:{i}")]
            for i, c in enumerate(hand) if c.is_playable_on(top)]
    btns.append([InlineKeyboardButton("🃏 Взяти карту", callback_data=f"draw:{cid}")])
    await ctx.bot.send_message(cid, f"Хід гравця {pid}. Карта: {top}", reply_markup=InlineKeyboardMarkup(btns))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    data = q.data.split(":"); action = data[0]; cid = int(data[1])
    pid = q.from_user.id; game = games.get(cid)
    if not game or pid != game.current_player():
        await q.edit_message_text("⛔ Не твій хід або гра завершена."); return

    if action == "draw":
        game.draw_cards(); await q.edit_message_text("🤚 Ти взяв карту.")
    elif action == "play":
        idx = int(data[2]); card = game.hands[pid][idx]
        if card.color == Color.WILD:
            opts = [[InlineKeyboardButton(col.value, callback_data=f"color:{cid}:{pid}:{idx}:{col.name}")]
                    for col in [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE]]
            await q.edit_message_text("Оберіть колір:", reply_markup=InlineKeyboardMarkup(opts)); return
        ok, played = game.play_card(pid, idx)
        if not ok: await q.edit_message_text(played); return
        await q.edit_message_text(f"🎴 Став: {played}")
    elif action == "color":
        pid2 = int(data[2]); idx = int(data[3]); col = Color[data[4]]
        _, played = game.play_card(pid2, idx, chosen_color=col)
        await q.edit_message_text(f"🎴 Став: {played} → {col.value}")

    next_pid = game.current_player()
    if game.has_uno(next_pid):
        await context.bot.send_message(cid,
             f"⚠️ Гравець {next_pid} має UNO! Хтось може його покарати.",
             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📣 UNO!", callback_data=f"uno:{cid}:{next_pid}")]]))
        return

    winner = game.has_winner()
    if winner:
        await context.bot.send_message(cid, f"🎉 {winner} виграв!") 
        games.pop(cid, None); return

    await prompt_move(context, cid)

async def handle_uno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.callback_query.data.split(":"); cid = int(parts[1]); uno_pid = int(parts[2])
    pid = update.callback_query.from_user.id
    if pid == uno_pid:
        await update.callback_query.answer("Не можна карати себе!"); return
    game = games.get(cid)
    if game and game.deck:
        game.hands[uno_pid].append(game.deck.pop())
    await update.callback_query.edit_message_text(f"🛑 Гравець {uno_pid} отримав штраф!")
    await prompt_move(context, cid)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CallbackQueryHandler(handle_uno, pattern="^uno:"))
    app.run_polling()

if __name__ == "__main__":
    import asyncio; asyncio.run(main())
