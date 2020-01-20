import re
import urllib.request

from bs4 import BeautifulSoup
from django.shortcuts import render

from main.models import Champion, Position, Skill, Tier
from whoosh import qparser
from whoosh.fields import DATETIME, TEXT, ID, NUMERIC, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, QueryParser


def getChampsInfo():
    url = 'https://euw.op.gg/champion/statistics'
    file = urllib.request.urlopen(url)
    parser = BeautifulSoup(file, 'html.parser')
    items = parser.find_all(lambda tag: tag.name == 'div' and 'champion-index__champion-item' in tag.get('class') and 'tip' not in tag.get('class'))
    for i in items:
        champ_stadics = i.find('a')['href']
        champ_stadics = 'https://euw.op.gg/' + champ_stadics
        file2 = urllib.request.urlopen(champ_stadics)
        parser2 = BeautifulSoup(file2, 'html.parser')
        champ_info = parser2.find('div', class_ = 'l-champion-statistics-header')
        name = champ_info.find('h1', class_ = 'champion-stats-header-info__name').string
        image = champ_info.find('div', class_ = 'champion-stats-header-info__image').find('img')['src']
        skills = champ_info.find_all('div', class_ = 'champion-stat__skill')
        skill_list = {}
        for s in skills:
            html_skill = s['title']
            html_skill = html_skill.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            parser_skill = BeautifulSoup(html_skill, 'html.parser')
            skill_name = parser_skill.find('b').string
            skill_description = parser_skill.find(lambda tag: tag.name == 'span' and not tag.attrs)
            if skill_description is None:
                skill_description = ''
            else:
                skill_description = skill_description.text
            skill_video = s.find('a')['href']
            description_and_video = [skill_description, skill_video]
            skill_list[skill_name] = description_and_video

        positions = champ_info.find_all('li', class_ = 'champion-stats-header__position')
        position_list = []
        for p in positions:
            position_list.append(p.find('span', class_ = 'champion-stats-header__position__role').string)
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
            champ_info = parser3.find('div', class_ = 'l-champion-statistics-header')
            tier = champ_info.find('div', class_ = 'champion-stats-header-info__tier').find('b').string
            tier = re.match(r'.*(\d)', tier)
            tier = tier.groups()[0]
            position_tier[p] = int(tier)

            counter_champs_html = champ_info.find_all('table', class_ = 'champion-stats-header-matchup__table')[0].find_all('tr')
            counter_champs = []
            for ch in counter_champs_html:
                counter_champs.append(ch.find('td', class_ = 'champion-stats-header-matchup__table__champion').text.replace('\n','').replace('\t',''))
            position_counters_champs[p] = counter_champs
            strong_against_champs = champ_info.find_all('table', class_ = 'champion-stats-header-matchup__table')[1].find_all('tr')
            strong_against = []
            for ch in strong_against_champs:
                strong_against.append(ch.find('td', class_ = 'champion-stats-header-matchup__table__champion').text.replace('\n','').replace('\t',''))
            position_strong_against_champs[p] = strong_against

        #Nombre del campeón -> string
            #Nombre de variable -> name
        #Imagen del campeón -> string
            #Nombre de variable -> image
        #Habilidades del campeón -> Diccionario {string, list} -> {nombre de la skill, [descripción, video]} #Debe haber siempre 5 skills
            #Nombre de variable -> skill_list
        #Tier según posición -> Diccionario {string, string} -> {posición, numero del tier}
            #Nombre de variable -> position_level
        #Campeones counters según posición -> Diccionario {string, list} -> {posición, [string, string, string]}
            #Nombre de variable -> position_counters_champs
        #Campeones fuertes contra según posición -> Diccionario {string, list} -> {posición, [string, string, string]}
            #Nombre de variable -> position_strong_against_champs

def schemaChampions():
    schema = Schema(idChampion = ID(stored=True),
                    name = TEXT(stored=True), 
                    image = TEXT(stored=True))
    return schema

def schemaSkill():
    schema = Schema(name = TEXT(stored=True), 
                    description = TEXT(stored=True),
                    video = TEXT(stored=True),
                    idChampion = ID(stored=True))
    return schema

def schemaPosition():
    schema = Schema(idPosition = ID(stored=True),
                    name = TEXT(stored=True))
    return schema

def schemaTier():
    schema = Schema(rating = NUMERIC(stored=True),
                    idChampion = ID(stored=True),
                    idPosition = ID(stored=True))
    return schema
