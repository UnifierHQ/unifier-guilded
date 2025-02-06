async def check(bot):
    try:
        await bot.guilded_client.close()
    except:
        # we can ignore this
        pass

    bot.guilded_client_task.cancel()

    try:
        del bot.guilded_client
    except:
        pass
