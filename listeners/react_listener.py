from valor import Valor
import discord
from util import ErrorEmbed, LongTextEmbed, info, LongFieldEmbed
from discord.utils import get
import time
from sql import ValorSQL
from dotenv import load_dotenv
import os

load_dotenv()

async def _register_react_listener(valor: Valor):
    @valor.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        # REQUIRES MEMBER INTENT TO BE ENABLED IN DISCORD SETTINGS
        msg_id = payload.message_id
        rxn_chn = valor.get_channel(payload.channel_id)

        if payload.user_id != int(os.environ["SELFID"]) and valor.reaction_msg_ids.get(msg_id, 0) > int(time.time()):
            emoji = str(payload.emoji)
            if len(emoji) == 1:
                emoji = ord(emoji)
            else:
                emoji = int(emoji.split(":")[-1][:-1])
            res = ValorSQL.get_react_msg_reaction(msg_id,  emoji)
            if not len(res):
                return
            
            res = res[0]

            if res[-1] == 'app':
                guild = valor.get_guild(payload.guild_id)
                config = ValorSQL.get_server_config(payload.guild_id)[0]
                category_id = config[1]
                category = get(guild.categories, id=category_id)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    payload.member: discord.PermissionOverwrite(read_messages=True),
                    # payload.member: discord.PermissionOverwrite(view_channel=True),
                    # payload.member: discord.PermissionOverwrite(send_messages=True),
                }

                chn = await guild.create_text_channel(f"app-{config[2]+1}", overwrites=overwrites, category=category)
                ValorSQL.server_config_set_app_cnt(payload.guild_id, config[2]+1)
                await chn.send(f"Hey, <@{payload.member.id}>", embed = LongTextEmbed("Fill This Out!", config[3], color=0xFFAA))

        # reaction to the green checkmark
        if payload.user_id != int(os.environ["SELFID"]):
            config = ValorSQL.get_server_config(payload.guild_id)
            if not len(config):
                return
            print("awef")
            config = config[0]
            if rxn_chn.category_id == config[1]:
                msg = rxn_chn.get_partial_message(payload.message_id)
                await msg.delete()

