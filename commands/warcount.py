import aiohttp, asyncio, time
from valor import Valor
from sql import ValorSQL
import discord
from util import ErrorEmbed, LongTextEmbed, LongTextTable
from discord.ext.commands import Context
from discord.ui import View
from discord import File
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
from dotenv import load_dotenv
import math, os
from commands.common import get_left_right, guild_names_from_tags
import argparse

load_dotenv()
async def _register_warcount(valor: Valor):
    desc = "Gets you the war count leaderboard. (old version)"
    clone_map = {"HUNTER": "ARCHER", "KNIGHT": "WARRIOR", "DARKWIZARD": "MAGE", "NINJA": "ASSASSIN", "SKYSEER": "SHAMAN"}
    clone_map_inv = {clone_map[k]: k for k in clone_map}
    real_classes = clone_map.values()
    parser = argparse.ArgumentParser(description='Warcount Command')
    parser.add_argument('-n', '--names', nargs='+', default=[])
    parser.add_argument('-a', '--guild_aggregate', action="store_true", default=False)
    parser.add_argument('-w', '--guild_wise', action="store_true", default=False)
    parser.add_argument('-g', '--guild', nargs='+', default=[]) # this one is filter players only in guilds, Callum: 100
    parser.add_argument('-c', '--classes', nargs='+', default=[])
    parser.add_argument('-r', '--range', nargs='+', default=None)
    parser.add_argument('-rk', '--rank', type=str, default="global")

    model_base = "https://visage.surgeplay.com/bust/"


    async def do_guild_aggregate_warcount(ctx: Context, opt):
        query = """
SELECT ROW_NUMBER() OVER(ORDER BY wars DESC) AS `rank`, B.tag, A.guild, CAST(A.wars AS UNSIGNED)
FROM
    (SELECT guild, SUM(delta) wars
    FROM
        player_delta_record
    WHERE label="g_wars" AND time >= %s AND time <= %s
    GROUP BY guild
    ORDER BY wars DESC LIMIT 100) A
    LEFT JOIN guild_tag_name B ON A.guild=B.guild;
"""
        start = time.time()
        if opt.range:
            # opt.range = [2e9, 0]
            valid_range = await get_left_right(opt, start)
            if valid_range == "N/A":
                return await ctx.send(embed=ErrorEmbed("Invalid season name input"))
            left, right = valid_range
        else:
            left, right = start - 3600*24*7, start

        rows = await ValorSQL.exec_param(query, (left, right))

        now = datetime.now()
        if opt.range:
            start_date = now - timedelta(days=float(opt.range[0]))
            end_date = now - timedelta(days=float(opt.range[1]))
        else:
            start_date = now - timedelta(days=7)  # Default to the last 7 days
            end_date = now
        time_range_str = f"{start_date.strftime('%d/%m/%Y %H:%M')} until {end_date.strftime('%d/%m/%Y %H:%M')}"
        delta_time = time.time() - start
        opt_after = f"\nQuery took {delta_time:.3}s. Requested at {datetime.utcnow().ctime()}\nRange: {time_range_str}"
        header = ['   ',  " Tag ", " "*16+"Guild ", "  Wars  "]

        return await LongTextTable.send_message(valor, ctx, header, rows, opt_after)
    
    async def do_guild_aggregate_captures(ctx: Context, opt):
        start = time.time()
        
        table_type = "cumu_warcounts" if not opt.range else "delta_warcounts"
        table_count_column = "warcount" if not opt.range else "warcount_diff"
        
        if opt.range:
            # opt.range = [2e9, 0]
            valid_range = await get_left_right(opt, start)
            if valid_range == "N/A":
                return await ctx.send(embed=ErrorEmbed("Invalid season name input"))
            left, right = valid_range
            
            query = f"""
SELECT ROW_NUMBER() OVER(ORDER BY captures DESC) AS `rank`, B.tag, A.guild, CAST(A.captures AS UNSIGNED)
FROM
    (SELECT player_stats.guild AS guild, SUM({table_type}.{table_count_column}) AS captures
    FROM {table_type}
    LEFT JOIN player_stats ON player_stats.uuid = {table_type}.uuid
    WHERE {table_type}.time >= %s AND {table_type}.time <= %s AND player_stats.guild IS NOT NULL
    GROUP BY player_stats.guild
    ORDER BY captures DESC LIMIT 100) A
    LEFT JOIN guild_tag_name B ON A.guild = B.guild;
"""
            rows = await ValorSQL.exec_param(query, (left, right))
        else:
            query = f"""
SELECT ROW_NUMBER() OVER(ORDER BY captures DESC) AS `rank`, B.tag, A.guild, CAST(A.captures AS UNSIGNED)
FROM
    (SELECT player_stats.guild AS guild, SUM({table_type}.{table_count_column}) AS captures
    FROM {table_type}
    LEFT JOIN player_stats ON player_stats.uuid = {table_type}.uuid
    WHERE player_stats.guild IS NOT NULL
    GROUP BY player_stats.guild
    ORDER BY captures DESC LIMIT 100) A
    LEFT JOIN guild_tag_name B ON A.guild = B.guild;
"""
            rows = await ValorSQL.exec_param(query, ())

        now = datetime.now()
        if opt.range:
            start_date = now - timedelta(days=float(opt.range[0]))
            end_date = now - timedelta(days=float(opt.range[1]))
        else:
            start_date = now - timedelta(days=7)
            end_date = now
        time_range_str = f"{start_date.strftime('%d/%m/%Y %H:%M')} until {end_date.strftime('%d/%m/%Y %H:%M')}"
        delta_time = time.time() - start
        opt_after = f"\nQuery took {delta_time:.3}s. Requested at {datetime.utcnow().ctime()}\nRange: {time_range_str}"
        header = ['   ',  " Tag ", " "*16+"Guild ", "  Warcounts  "]

        return await LongTextTable.send_message(valor, ctx, header, rows, opt_after)
    
    def basic_table(header: list[str], data: list[tuple], page: int, footer: str) -> str:
        start = page * 10
        end = start + 10
        sliced = data[start:end]

        col_widths = [len(h) for h in header]
        lines = []

        fmt = ' ┃ '.join(f"%{len(x)}s" for x in header)
        header_line = fmt % tuple(header)
        lines.append(header_line)

        separator = ''.join('╋' if x == '┃' else '━' for x in header_line)
        lines.append(separator)

        for row in sliced:
            line = ""
            for i, cell in enumerate(row):
                line += str(cell).rjust(col_widths[i])
                if i != len(row) - 1:
                    line += " ┃ "
            lines.append(line)

        lines.append(separator)
        lines.append(footer)

        return "```" + "\n".join(lines) + "```"

    async def download_model(session, url, filename):
        user_agent = {'User-Agent': 'valor-bot/1.0'}
        try:
            async with session.get(url, headers=user_agent) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(filename, "wb") as f:
                        f.write(content)
                else:
                    print(f"Failed to fetch {url}: {response.status}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    async def fetch_all_models(rows):
        tasks = []
        now = time.time()
        async with aiohttp.ClientSession() as session:
            for row in rows:
                if row[1]:
                    filename = f"/tmp/{row[1]}_model.png"
                    url = model_base + row[1] + '.png'

                    if not os.path.exists(filename) or now - os.path.getmtime(filename) > 24 * 3600:
                        tasks.append(download_model(session, url, filename))
            await asyncio.gather(*tasks)  # Run all downloads in parallel


    async def fancy_table(data: list[tuple], listed_classes: list, page: int):
        start = page * 10
        end = start + 10
        sliced = data[start:end]

        img = Image.open("assets/warcount_template.png")
        draw = ImageDraw.Draw(img)

        name_fontsize = 20
        text_fontsize = 16
        total_fontsize = 18
        name_font = ImageFont.truetype("assets/MinecraftRegular.ttf", name_fontsize)
        text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", text_fontsize)
        total_font = ImageFont.truetype("assets/MinecraftRegular.ttf", total_fontsize)

        await fetch_all_models(sliced)

        i = 1
        for row in sliced:
            y = ((57*(i/2))+(59*(i/2)))+27

            color = "white"
            match row[0]:
                case 1:
                    color = "yellow"
                case 2:
                    color = (170,169,173,255)
                case 3:
                    color = (169,113,66,255)

            draw.text((62, y), f"{row[0]}.", color, total_font, anchor="rm")
            draw.text((153, y), row[1], "white", name_font, anchor="lm")

            try:
                model_img = Image.open(f"/tmp/{row[1]}_model.png", 'r')
                model_img = model_img.resize((54, 54))
            except Exception as e:
                model_img = Image.open(f"assets/unknown_model.png", 'r')
                model_img = model_img.resize((54, 54))
                print(f"Error loading image: {e}")

            img.paste(model_img, (84, int(y)-29), model_img)

            draw.text((445, y), row[2], "white", total_font, anchor="mm")
            x = 0

            if "ARCHER" in listed_classes:
                draw.text((532, y), str(row[3+x]), "white", text_font, anchor="mm")
                x += 1
            if "WARRIOR" in listed_classes:
                draw.text((593, y), str(row[3+x]), "white", text_font, anchor="mm")
                x += 1
            if "MAGE" in listed_classes:
                draw.text((658, y), str(row[3+x]), "white", text_font, anchor="mm")
                x += 1
            if "ASSASSIN" in listed_classes:
                draw.text((718, y), str(row[3+x]), "white", text_font, anchor="mm")
                x += 1
            if "SHAMAN" in listed_classes:
                draw.text((780, y), str(row[3+x]), "white", text_font, anchor="mm")
                x += 1

            draw.text((827, y), str(row[3+x]), "white", total_font, anchor="lm")

            i += 1
        
        img.save("/tmp/warcount.png")
        file = File("/tmp/warcount.png", filename="warcount.png")
        return file

    class WarcountView(View):
        def __init__(self, ctx, header, rows, listed_classes, footer, timeout=60):
            super().__init__(timeout=timeout)
            self.ctx = ctx
            self.is_fancy = False
            self.listed_classes = listed_classes

            self.page = 0
            self.header = header
            self.data = rows
            self.footer = footer
            
            self.max_pages = math.ceil(len(rows) / 10)

        async def update_message(self, interaction: discord.Interaction):
            if self.is_fancy:
                await interaction.response.defer()
                content = await fancy_table(self.data, self.listed_classes, self.page)
                await interaction.edit_original_response(content="", view=self, attachments=[content])
            else:
                content = basic_table(self.header, self.data, self.page, self.footer)
                await interaction.response.edit_message(content=content, view=self, attachments=[])

        @discord.ui.button(label="⬅️")
        async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
                await self.update_message(interaction)
            else:
                await interaction.response.defer()

        @discord.ui.button(label="➡️")
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page < self.max_pages - 1:
                self.page += 1
                await self.update_message(interaction)
            else:
                await interaction.response.defer()
        
        @discord.ui.button(label="✨")
        async def fancy(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.is_fancy = not self.is_fancy
            await self.update_message(interaction)
            

    @valor.command()
    async def warcount(ctx: Context, *options):
        try:
            opt = parser.parse_args(options)
        except:
            return await LongTextEmbed.send_message(valor, ctx, "warcount", parser.format_help().replace("main.py", "-warcount"), color=0xFF00)
    
        if opt.guild_aggregate:
            return await do_guild_aggregate_warcount(ctx, opt)
        elif opt.guild_wise:
            return await do_guild_aggregate_captures(ctx, opt)
        
        listed_classes = real_classes if not opt.classes else opt.classes
        listed_classes = [x.upper() for x in listed_classes]
        listed_classes_enumerated = {v.upper(): i for i, v in enumerate(listed_classes)} # {classname: 0, classname: 1, ...}

        names = {n.upper() for n in opt.names} if opt.names else None

        start = time.time()

        table_type = "cumu_warcounts" if not opt.range else "delta_warcounts"
        table_count_column = "warcount" if not opt.range else "warcount_diff"

        warcount_query = f'''SELECT uuid_name.name, 
    %s,
	SUM({table_type}.{table_count_column}) as all_wars, 
	player_stats.guild
FROM {table_type} 
LEFT JOIN uuid_name ON uuid_name.uuid={table_type}.uuid 
LEFT JOIN player_stats ON player_stats.uuid={table_type}.uuid 
WHERE UPPER({table_type}.class_type) IN (%s) %%s 
GROUP BY uuid_name.uuid, player_stats.guild
ORDER BY all_wars DESC;'''
        
        class_column_count_parts = []
        select_class_in_parts = []
        for real_class in listed_classes:
            class_column_count_parts.append( # lol the dict lookup will fail if user tries some tricky sql input
                f"SUM(CASE WHEN UPPER({table_type}.class_type)='{real_class}' OR UPPER({table_type}.class_type)='{clone_map_inv[real_class]}' THEN {table_type}.{table_count_column} ELSE 0 END) AS {real_class}_count")
            select_class_in_parts.append(f"'{real_class}', '{clone_map_inv[real_class]}'")
        
        warcount_query = warcount_query % (','.join(class_column_count_parts), ','.join(select_class_in_parts))

        if opt.range:
            # opt.range = [2e9, 0]
            valid_range = await get_left_right(opt, start)
            if valid_range == "N/A":
                return await ctx.send(embed=ErrorEmbed("Invalid season name input"))
            left, right = valid_range

            res = await ValorSQL._execute(warcount_query % f' AND delta_warcounts.time >= {left} AND delta_warcounts.time <= {right}')
        else:
            res = await ValorSQL._execute(warcount_query % '')

        delta_time = time.time()-start
        
        guild_names, unidentified = await guild_names_from_tags(opt.guild)

        header = ['  Rank  ', ' '*14+"Name", "Guild", *[f"  {x}  " for x in listed_classes], "  Total  "]

        player_to_guild = {}
        guilds_seen = set()
        player_warcounts = {}

        name_to_ranking = {}

        for rank_0, row in enumerate(res):
            name, total, guild = row[0], row[-2], row[-1]
            name_to_ranking[name] = rank_0+1
            classes_count = row[1:-2]

            if opt.guild and not guild in guild_names: continue
            if not name or (opt.names and not name.upper() in names): continue
            if not name in player_warcounts:
                player_warcounts[name] = [0]*len(listed_classes_enumerated)

            for i, real_class in enumerate(listed_classes):
                player_warcounts[name][listed_classes_enumerated[real_class]] += classes_count[i]

            player_to_guild[name] = guild
            guilds_seen.add(guild)
        
        guild_to_tag = {}
        if guilds_seen:
            expanded_guilds_str = ','.join(f"'{x}'" for x in guilds_seen) # TODO: batch req size 50
            res = await ValorSQL._execute(f'SELECT guild, tag, priority FROM guild_tag_name WHERE guild IN ({expanded_guilds_str})')
            for guild, tag, priority in res:
                if priority > guild_to_tag.get(guild, ("N/A", -1))[1]:
                    guild_to_tag[guild] = (tag, priority)


        if opt.rank != "global":
            rows_total_count = [(name, sum(player_warcounts[name])) for name in player_warcounts]
            rows_total_count.sort(key=lambda x: x[-1], reverse=True) 
            name_to_ranking = {}
            for i, rest in enumerate(rows_total_count):
                name_to_ranking[rest[0]] = i+1
        
        rows = [(name_to_ranking[name], name, guild_to_tag.get(player_to_guild[name], ("None", -1))[0], *player_warcounts[name], sum(player_warcounts[name])) for name in player_warcounts]
        rows.sort(key=lambda x: x[-1], reverse=True)

        if not rows:
            return await ctx.send(embed=ErrorEmbed("No results, wrong username? have they done no wars?"))

        now = datetime.now()
        if opt.range:
            start_date = now - timedelta(days=float(opt.range[0]))
            end_date = now - timedelta(days=float(opt.range[1]))
        else:
            start_date = now - timedelta(days=7)  # Default to the last 7 days
            end_date = now
        time_range_str = f"{start_date.strftime('%d/%m/%Y %H:%M')} until {end_date.strftime('%d/%m/%Y %H:%M')}"
        opt_after = f"\nQuery took {delta_time:.3}s. Requested at {datetime.utcnow().ctime()}\nRange: {time_range_str}"
        view = WarcountView(ctx, header, rows, listed_classes, opt_after)
        await ctx.send(content=basic_table(header, rows, 0, opt_after), view=view)

    @valor.help_override.command()
    async def warcount(ctx: Context):
        await LongTextEmbed.send_message(valor, ctx, "Warcount", desc, color=0xFF00)
