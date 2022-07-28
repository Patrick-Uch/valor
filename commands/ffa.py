from valor import Valor
from discord.ext.commands import Context
import discord
from util import ErrorEmbed, LongTextEmbed, LongFieldEmbed
from datetime import datetime
import commands.common
import os
from dotenv import load_dotenv

load_dotenv()
TEST = os.getenv("TEST")=="TRUE"

async def _register_ffa(valor: Valor):
    desc = "Pings ffa role"
    
    @valor.command()
    async def ffa(ctx: Context, *msg):
        if not commands.common.role1(ctx.author, allow={536068288606896128}) and not TEST:
            return await ctx.send(embed=ErrorEmbed("No Permissions. (you need military role)"))
    
        await ctx.send(f'''<@&892884695199666187> {" ".join(msg)}''', 
            embed=LongTextEmbed(title="FFA Ping", content="<insert whatever the ffa copypasta is rn> to War!!! \nI'm using some insane algorithm to predict that Aiza is pinging this at 3am", color=0xFF8888))
    
    # other war pings
    @valor.command()
    async def dps(ctx: Context, *msg):
        if not commands.common.role1(ctx.author, allow={536068288606896128}) and not TEST:
            return await ctx.send(embed=ErrorEmbed("No Permissions. (you need military role)"))
    
        await ctx.send(f'''<@&892885182300954624> {" ".join(msg)}''', 
            embed=LongTextEmbed(title="DPS Ping", content="DPS (damage per second) needed", color=0xFF8888))
    
    @valor.command()
    async def guardian(ctx: Context, *msg):
        if not commands.common.role1(ctx.author, allow={536068288606896128}) and not TEST:
            return await ctx.send(embed=ErrorEmbed("No Permissions. (you need military role)"))
    
        await ctx.send(f'''<@&892884953996591164> {" ".join(msg)}''', 
            embed=LongTextEmbed(title="Guardian Ping", content="Guardian needed", color=0xFF8888))
    
    @valor.command()
    async def healer(ctx: Context, *msg):
        if not commands.common.role1(ctx.author, allow={536068288606896128}) and not TEST:
            return await ctx.send(embed=ErrorEmbed("No Permissions. (you need military role)"))
    
        await ctx.send(f'''<@&892885381744320532> {" ".join(msg)}''', 
            embed=LongTextEmbed(title="Healer Ping", content="Healer needed", color=0xFF8888))
    
    @valor.command()
    async def trg(ctx: Context, *msg):
        if not commands.common.role1(ctx.author, allow={536068288606896128}) and not TEST:
            return await ctx.send(embed=ErrorEmbed("No Permissions. (you need military role)"))
    
        await ctx.send(f'''<@&683785435117256939> {" ".join(msg)}''', 
            embed=LongTextEmbed(title="Healer Ping", content="Royal Guard Ping", color=0xFF8888))

    @valor.help_override.command()
    async def ffa(ctx: Context):
        await LongTextEmbed.send_message(valor, ctx, "ffa", desc, color=0xFF00)
    
    
    
