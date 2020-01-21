import re

import urllib.request
import re
import os
from bs4 import BeautifulSoup
from django.shortcuts import render

from whoosh import qparser
from whoosh.fields import DATETIME, TEXT, ID, NUMERIC, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, QueryParser
from django.conf import settings

from main.models import Champion, Skill, Position, Tier, Players


def index(request):
    return render(request, 'index.html', {'STATIC_URL': settings.STATIC_URL})


def getChampsInfo():
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    skills_directory = main_directory + '/' + 'skills'
    positions_directory = main_directory + '/' + 'positions'
    tiers_directory = main_directory + '/' + 'tiers'
    if not os.path.exists(main_directory):
        os.mkdir(main_directory)
    if not os.path.exists(champions_directory):
        os.mkdir(champions_directory)
    if not os.path.exists(skills_directory):
        os.mkdir(skills_directory)
    if not os.path.exists(positions_directory):
        os.mkdir(positions_directory)
    if not os.path.exists(tiers_directory):
        os.mkdir(tiers_directory)

    ix1 = create_in(champions_directory, schema=schemaChampions())
    ix2 = create_in(skills_directory, schema=schemaSkill())
    ix3 = create_in(positions_directory, schema=schemaPosition())
    ix4 = create_in(tiers_directory, schema=schemaTier())
    writer1 = ix1.writer()
    writer2 = ix2.writer()
    writer3 = ix3.writer()
    writer4 = ix4.writer()

    # Añadimos las posiciones al esquema de posiciones
    writer3.add_document(idPosition=1, name='Bot')
    writer3.add_document(idPosition=2, name='Mid')
    writer3.add_document(idPosition=3, name='Jungle')
    writer3.add_document(idPosition=4, name='Top')
    writer3.add_document(idPosition=5, name='Support')
    writer3.commit()
    print('Se han indexado ' + str(5) + ' posiciones')

    # Empezamos el scraping de los campeones y su información
    count_champion = 1
    count_skill = 1
    url = 'https://euw.op.gg/champion/statistics'
    file = urllib.request.urlopen(url)
    parser = BeautifulSoup(file, 'html.parser')
    champions = parser.find_all(
        lambda tag: tag.name == 'div' and 'champion-index__champion-item' in tag.get('class') and 'tip' not in tag.get('class'))

    # Diccionarios para almacenar datos temporalmente
    name_id_champ = {}
    name_positions_champ = {}
    name_position_tier = {}
    name_position_counters_champs = {}
    name_position_strong_against_champs = {}
    for c in champions:
        champ_stadics = c.find('a')['href']
        champ_stadics = 'https://euw.op.gg/' + champ_stadics
        file2 = urllib.request.urlopen(champ_stadics)
        parser2 = BeautifulSoup(file2, 'html.parser')
        champ_info = parser2.find('div', class_='l-champion-statistics-header')

        # Nombre e imagen del campeón
        champ_name = champ_info.find(
            'h1', class_='champion-stats-header-info__name').string
        champ_image = champ_info.find(
            'div', class_='champion-stats-header-info__image').find('img')['src']
        name_id_champ[champ_name] = count_champion

        # Habilidades del campeón
        skills = champ_info.find_all('div', class_='champion-stat__skill')
        for s in skills:
            html_skill = s['title']
            html_skill = html_skill.replace('<br>', '\n').replace(
                '<br/>', '\n').replace('<br />', '\n')
            parser_skill = BeautifulSoup(html_skill, 'html.parser')
            skill_name = parser_skill.find('b').string
            skill_description = parser_skill.find(
                lambda tag: tag.name == 'span' and not tag.attrs)
            if skill_description is None:
                skill_description = ''
            else:
                skill_description = skill_description.text
            skill_video = s.find('a')['href']

            # Añadimos las hablidades al esquema de habilidades
            writer2.add_document(name=skill_name, description=skill_description,
                                 video=skill_video, idChampion=count_champion)
            count_skill = count_skill + 1

        # Posiciones del campeón
        positions = champ_info.find_all(
            'li', class_='champion-stats-header__position')
        position_list = []
        for p in positions:
            position_list.append(
                p.find('span', class_='champion-stats-header__position__role').string)
        name_positions_champ[champ_name] = position_list
        position_tier = {}
        position_counters_champs = {}
        position_strong_against_champs = {}
        for p in position_list:
            if p == 'Middle':
                p = 'Mid'
            if p == 'Bottom':
                p = 'Bot'
            champ_position_url = champ_stadics + '/' + p
            file3 = urllib.request.urlopen(champ_position_url)
            parser3 = BeautifulSoup(file3, 'html.parser')
            champ_info = parser3.find(
                'div', class_='l-champion-statistics-header')

            # Nivel del campeón según la posición
            tier = champ_info.find(
                'div', class_='champion-stats-header-info__tier').find('b').string
            tier = re.match(r'.*(\d)', tier)
            tier = tier.groups()[0]
            position_tier[p] = int(tier)

            # Campeones contra los que es débil el campeón "c" según la posición
            counter_champs_html = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[0].find_all('tr')
            counter_champs = []
            for ch in counter_champs_html:
                counter_champs.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_counters_champs[p] = counter_champs

            # Campeones contra los que es fuerte el campeón "c" según la posición
            strong_against_champs = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[1].find_all('tr')
            strong_against = []
            for ch in strong_against_champs:
                strong_against.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_strong_against_champs[p] = strong_against

        # Se guarda un diccionario relacionado con cada nombre y otro diccionario de tier, counters y strongs según la posición
        name_position_tier[champ_name] = position_tier
        name_position_counters_champs[champ_name] = position_counters_champs
        name_position_strong_against_champs[champ_name] = position_strong_against_champs

        # Añadimos los campeones al esquema de campeones
        writer1.add_document(idChampion=count_champion, name=str(
            champ_name), image=str(champ_image))
        count_champion = count_champion + 1

    print('Se han indexado ' + str(count_champion-1) + ' campeones')
    print('Se han indexado ' + str(count_skill-1) + ' habilidades')
    writer1.commit()
    writer2.commit()

    # Añadimos los niveles al esquema de niveles
    # En idsChampionCounter e idsChampionStronger se guardan en string separado por comas las ids de los campeones
    ix_champs = open_dir(champions_directory)
    ix_positions = open_dir(positions_directory)
    count_tier = 1
    with ix_champs.searcher() as searcher_champs:
        doc_champs = searcher_champs.documents()
        for dc in doc_champs:
            position_tier = name_position_tier[dc['name']]
            for p in position_tier.keys():  # En p tengo la posición (Mid, Top, etc) que tenga el campeón
                position_counters_champs = name_position_counters_champs[dc['name']]
                position_strong_against_champs = name_position_strong_against_champs[dc['name']]
                ids_champions_counters = []
                ids_champions_strongers = []
                for pcc in position_counters_champs[p]:
                    query = QueryParser(
                        'name', ix_champs.schema).parse(str(pcc))
                    doc_champs_results = searcher_champs.search(query)
                    ids_champions_counters.append(
                        str(doc_champs_results[0]['idChampion']))
                for psac in position_strong_against_champs[p]:
                    query = QueryParser(
                        'name', ix_champs.schema).parse(str(psac))
                    doc_champs_results = searcher_champs.search(query)
                    ids_champions_strongers.append(
                        str(doc_champs_results[0]['idChampion']))
                seperator = ', '
                ids_champions_counters = seperator.join(ids_champions_counters)
                ids_champions_strongers = seperator.join(
                    ids_champions_strongers)
                with ix_positions.searcher() as searcher_positions:
                    query = QueryParser(
                        'name', ix_positions.schema).parse(str(p))
                    doc_positions_results = searcher_positions.search(query)
                    writer4.add_document(level=position_tier[p], idChampion=name_id_champ[dc['name']], idPosition=doc_positions_results[0]['idPosition'],
                                         idsChampionCounter=ids_champions_counters, idsChampionStronger=ids_champions_strongers)
                    count_tier = count_tier + 1
    writer4.commit()
    print('Se han indexado ' + str(count_tier-1) +
          ' niveles según la posición del campeón')


def getPlayerInfo():
    main_directory = 'info_champ'
    players_directory = main_directory + '/' + 'players'
    if not os.path.exists(main_directory):
        os.mkdir(main_directory)
    if not os.path.exists(players_directory):
        os.mkdir(players_directory)
    ix1 = create_in(players_directory, schema=schemaPlayers())
    writer1 = ix1.writer()
    page = 1
    limit = 8
    count_players = 1
    while(page <= limit):
        # Accedemos a la página
        url = 'https://euw.op.gg/ranking/ladder/page=' + str(page)
        file = urllib.request.urlopen(url)
        parser = BeautifulSoup(file, 'html.parser')
        # Sacar los datos de los más altos solo si es la primera página
        if page == 1:
            higher = parser.find_all('li', class_='ranking-highest__item')
            for h in higher:
                higher_name = h.find('a', class_='ranking-highest__name').text
                higher_url = h.find(
                    'a', class_='ranking-highest__name')['href']
                higher_url = 'https:' + higher_url
                ranking = h.find(
                    'div', class_='ranking-highest__tierrank').find('span').text.strip()
                winrate = h.find('span', class_='winratio__text').text
                winrate = int(winrate.replace('%', ''))

                # Se accede a su url y se sacan sus campeones jugados
                file2 = urllib.request.urlopen(higher_url)
                parser2 = BeautifulSoup(file2, 'html.parser')
                champs = parser2.find_all('div', class_='GameItemWrap')
                champ_list_id = []

                # Se iteran los campeones y por cada uno se coge su id y se almacena en la lista
                for champ in champs:
                    champ_name = champ.find(
                        'div', class_='ChampionName').text.strip()
                    # Llamada al método para recuperar el id
                    id_champ = getIdByChampionName(champ_name)
                    champ_list_id.append(str(id_champ))
                seperator = ', '
                champ_list_id = seperator.join(champ_list_id)
                # Se guarda el jugador
                writer1.add_document(idPlayer=count_players, name=higher_name, urlPerfil=higher_url,
                                     ranking=ranking, winrate=winrate, idsChampion=champ_list_id)
                # Se incrementa el id del jugador
                count_players = count_players + 1

        # Se sacan el resto de jugadores
        normal_table = parser.find_all('tr', class_='ranking-table__row')
        for row in normal_table:
            normal_name = row.find(
                'td', class_='select_summoner ranking-table__cell ranking-table__cell--summoner').find('span').text
            normal_url = row.find(
                'td', class_='select_summoner ranking-table__cell ranking-table__cell--summoner').find('a')['href']
            normal_url = 'https:' + normal_url
            normal_ranking = row.find(
                'td', class_='ranking-table__cell ranking-table__cell--tier').text.strip()
            normal_winrate = row.find(
                'span', class_='winratio__text').text.strip()
            normal_winrate = int(normal_winrate.replace('%', ''))
            # Se accede a su url y se sacan sus campeones jugados
            file2 = urllib.request.urlopen(higher_url)
            parser2 = BeautifulSoup(file2, 'html.parser')
            champs = parser2.find_all('div', class_='GameItemWrap')
            champ_list_id = []
            # Se iteran los campeones y por cada uno se coge su id y se almacena en la lista
            for champ in champs:
                champ_name = champ.find(
                    'div', class_='ChampionName').text.strip()
                champ_list_id = []
                # Llamada al método para recuperar el id
                id_champ = getIdByChampionName(champ_name)
                champ_list_id.append(str(id_champ))
            seperator = ', '
            champ_list_id = seperator.join(champ_list_id)
            # Se guarda el jugador
            writer1.add_document(idPlayer=count_players, name=normal_name, urlPerfil=normal_url,
                                 ranking=normal_ranking, winrate=normal_winrate, idsChampion=champ_list_id)
            # Se incrementa el id del jugador
            count_players = count_players + 1
        # Se incrementa para acceder a la siguiente página
        page = page + 1
    writer1.commit()
    print('Se han indexado ' + str(count_players-1) + ' jugadores')


def schemaChampions():
    schema = Schema(idChampion=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    image=TEXT(stored=True))
    return schema


def schemaSkill():
    schema = Schema(name=TEXT(stored=True),
                    description=TEXT(stored=True),
                    video=TEXT(stored=True),
                    idChampion=NUMERIC(stored=True))
    return schema


def schemaPosition():
    schema = Schema(idPosition=NUMERIC(stored=True),
                    name=TEXT(stored=True))
    return schema


def schemaTier():
    schema = Schema(level=NUMERIC(stored=True),
                    idChampion=NUMERIC(stored=True),
                    idPosition=NUMERIC(stored=True),
                    idsChampionCounter=TEXT(stored=True),
                    idsChampionStronger=TEXT(stored=True))
    return schema


def schemaPlayers():
    schema = Schema(idPlayer=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    urlPerfil=TEXT(stored=True),
                    ranking=TEXT(stored=True),
                    winrate=NUMERIC(stored=True),
                    idsChampion=TEXT(stored=True))
    return schema


def populate_champion():
    print("Loading champions...")
    Champion.objects.all().delete()
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    lista = []
    ix = open_dir(champions_directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            lista.append(
                Champion(idChampion=row['idChampion'], name=row['name'], image=row['image']))
    Champion.objects.bulk_create(lista)
    print("Ratings inserted: " + str(Champion.objects.count()))
    print("---------------------------------------------------------")


def getIdByChampionName(champ_name):
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    ix = open_dir(champions_directory)
    with ix.searcher() as searcher:
        entry = str(champ_name)
        query = QueryParser('name', ix.schema).parse(entry)
        results = searcher.search(query)
        row = results[0]
        id = row['idChampion']
    return id


def list_campeones(request):
    campeones = Champion.objects.all().order_by('name')
    return render(request, 'list_campeones.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def list_jugadores(request):
    jugadores = Players.objects.all().order_by('name')
    return render(request, 'list_jugadores.html', {'jugadores': jugadores, 'STATIC_URL': settings.STATIC_URL})


def mejores_campeones(request):
    return render(request, 'mejores_campeones.html', {'STATIC_URL': settings.STATIC_URL})


def mejores_jugadores(request):
    return render(request, 'mejores_jugadores.html', {'STATIC_URL': settings.STATIC_URL})



populate_champion()