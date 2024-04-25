async def check(bot):
    await bot.guilded_client.close()
    bot.guilded_client_task.cancel()
    del bot.guilded_client