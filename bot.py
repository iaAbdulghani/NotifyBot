import os
from dotenv import load_dotenv
import discord
import pymongo
from bs4 import BeautifulSoup
import requests
import sys
import time
from discord.ext import tasks




def run_discord_bot():

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '.env')) 
    load_dotenv(dotenv_path)
    
    TOKEN = os.environ.get("TOKEN")
    DATABASE = os.environ.get("DATABASE")

    dbClient = pymongo.MongoClient(DATABASE)
    db = dbClient.test
    
    @client.event
    async def on_ready():
        print(f'{client.user} is now running!')
        checkWebsite.start()
        updateList.start()
        
        
    @tasks.loop(seconds = 60)
    async def checkWebsite():
        URL = "https://zoro.to/recently-updated"
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        main = soup.find(id="main-content")
        names = main.find_all('a', class_="dynamic-name")
        nums = main.find_all('div', class_="tick-item tick-eps")
        
            
        for i in range(0, len(names)):
            if(db.episodes.count_documents({ "_id": (names[i].text.strip()+ nums[i].text.strip())})==0):
                db.episodes.insert_one({
                     "_id": (names[i].text.strip()+ nums[i].text.strip())
                })
                for one in db.shows.find({"_id": (names[i].text.strip())}):
                    for id in one["users"]:
                        user = await client.fetch_user(id)
                        await user.send(nums[i].text.strip()+" of "+names[i].text.strip()+" has released")
                    
        
        
    @tasks.loop(seconds=86400)
    async def updateList():
        db.names.delete_many({})
        URL = "https://zoro.to/top-upcoming"
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        main = soup.find(id="main-content")
        names = main.find_all('a', class_="dynamic-name")
        
        for name in names: 
            db.names.insert_one({
                "name": name.text})
            db.shows.update_one(
                {"_id": name.text},
                {"$setOnInsert" : {"users": []}},
                upsert=True)
            
        URL = "https://zoro.to/top-airing"
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        main = soup.find(id="main-content")
        names = main.find_all('a', class_="dynamic-name")
        for name in names:
            db.names.insert_one({
                "name": name.text
            })
            db.shows.update_one(
                {"_id": name.text},
                {"$setOnInsert" : {"users": []}},
                upsert=True)
                                
        
            

    
    @client.event
    async def on_message(message):
        
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content).strip().lower()
        channel = str(message.channel)

        if user_message.startswith('anya help'):
            await message.channel.send("Type `Anya view list` to see the names of all available shows.\nType `Anya add [show name]` to add a new show to your list.\nType `Anya remove [show name]` to remove a show from your list.\nType `Anya mylist` to view which shows you are currently watching.")


        elif user_message.startswith ('anya view list'):
           names = db.names
           index = 1
           sys.stdout = open("output.txt", 'w')
           for name in names.find():
               sys.stdout.write(str(index)+": "+ name['name']+"\n")
               index+=1
           sys.stdout.close()
           await message.channel.send(file=discord.File("output.txt"))
           
        elif user_message.startswith ('anya add'):
            show = user_message[9:]
            names = db.names
            for name in names.find():
               if str(name["name"]).lower()==show:
                   db.shows.update_one(
                        {"_id":str(name["name"])},
                        {"$addToSet": {"users": message.author.id}}
                    )
                   db.users.update_one(
                    {"_id": message.author.id},
                    {"$setOnInsert" : {"shows": []}},
                    upsert=True)
                   db.users.update_one(
                        {"_id":message.author.id},
                        {"$addToSet": {"shows": str(name["name"])}}
                    )
                   
                   await message.channel.send(name["name"]+" has been added to your list. If it was already there, nothing has changed.")
                   return
            await message.channel.send("That name is not on the list. Use `anya view list` to view all the anime I keep track of.")

        elif user_message.startswith('anya remove'):
            show = user_message[12:]
            names = db.names
            for name in names.find():
                   if str(name["name"]).lower()==show:
                        db.shows.update_one(
                            {"_id":str(name["name"])},
                            {"$pull": {"users": message.author.id}}
                        )
                   
                        db.users.update_one(
                            {"_id":message.author.id},
                            {"$pull": {"shows": str(name["name"])}}
                        )
                   
                        await message.channel.send(name["name"]+" has been removed from your list. If it was not already there, nothing has changed.")
                        return
            await message.channel.send("That name is not on the list. Use `anya view list` to view all the anime I keep track of.")
            
        elif user_message.startswith('anya mylist'):
            for one in db.users.find({"_id": message.author.id}):
                for show in one["shows"]:
                     await message.channel.send(show)
                    
                
            


    client.run(TOKEN)