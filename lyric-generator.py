#! /usr/local/bin/python3

# -*- coding: utf-8 -*-


'''
A script that scraps Genius site using the Genius API 
and beautiful soup for the lyrics of any given artist.
New lyrics are then generated using markov chain analyis 
the results are dumped to output text file.

args:
-c --credentials Path to the credentials file
-a --artist Name of the artist
-o --output Path to the output new lyrics file
-s --start Start word
-n --number Number of words

'''

try:
	import urllib.request as urllib2
except ImportError:
	import urllib2

import sys  
import re
import json
import os
import socket
import argparse
import random, re

import requests
from bs4 import BeautifulSoup

from collections import Counter

class LyricScraper:
	"""Lyric Scraper class"""
	def __init__(self, credentials_file, output_file):
		self.credentials_file = credentials_file
		self.output_file = output_file
		lines = [line.rstrip('\n') for line in open(self.credentials_file)]
		chars_to_strip = " \'\""
		for line in lines:
			if "client_id" in line:
					client_id = re.findall(r'[\"\']([^\"\']*)[\"\']', line)[0]
			if "client_secret" in line:
					client_secret = re.findall(r'[\"\']([^\"\']*)[\"\']', line)[0]
			if "client_access_token" in line:
					client_access_token = re.findall(r'[\"\']([^\"\']*)[\"\']', line)[0]
		self.client_access_token=client_access_token
		self.client_secret=client_secret
		self.client_id=client_id


	def get_artist_id(self,search_term,num_pages=25):
		# get_artist_id
		# method to check first num_pages of results for a 
		# search query and finds the most common artist id
		mycounter = Counter()
		for i in range(num_pages):
			querystring = "http://api.genius.com/search?q=" + urllib2.quote(search_term) + "&page=" + str(i+1)
			request = urllib2.Request(querystring)
			request.add_header("Authorization", "Bearer " + self.client_access_token)   
			request.add_header("User-Agent", "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)") #Must include user agent of some sort, otherwise 403 returned
			while True:
				try:
					response = urllib2.urlopen(request, timeout=4) #timeout set to 4 seconds; automatically retries if times out
					raw = response.read()
				except socket.timeout:
					print("Timeout raised and caught")
					continue
				break
			json_obj = json.loads(raw)
			body = json_obj["response"]["hits"]
			num_hits = len(body)
			if num_hits==0:
				if i==0:
					print("No results for: " + search_term)
				break
			for result in body:
				primaryartist_id = result["result"]["primary_artist"]["id"]
				primaryartist_name = result["result"]["primary_artist"]["name"]
				primaryartist_url = result["result"]["primary_artist"]["url"]
				if primaryartist_name.lower() == search_term.lower() :
					mycounter[primaryartist_id]+=1
		artist_id=mycounter.most_common()
		return artist_id[0][0]


	def get_artists_songs(self,artists_id):
		# get_artists_songs
		# method to get a list of api paths for all the songs of 
		# a given artists_id	
		api_paths=[]
		querystring = "http://api.genius.com/artists/" + urllib2.quote(str(artists_id)) + "/songs"
		request = urllib2.Request(querystring)
		request.add_header("Authorization", "Bearer " + self.client_access_token)   
		request.add_header("User-Agent", "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)") #Must include user agent of some sort, otherwise 403 returned
		try:
			response = urllib2.urlopen(request, timeout=4) #timeout set to 4 seconds; automatically retries if times out
			raw = response.read()
		except socket.timeout:
			print("Timeout raised and caught")
			return None
		json_obj = json.loads(raw)
		body = json_obj["response"]["songs"]
		num_hits = len(body)
		if num_hits==0:
			if page==1:
				print("No results for: " + search_term)
				return None
		for result in body:
			api_paths.append(result['api_path'])
		return api_paths


	def get_lyrics(self,api_paths):
		# get_lyrics
		# method to get a list of lyrics in txt from a 
		# given list of api_paths	
		base_url = "http://api.genius.com"
		lyrics=[]
		for song in api_paths:
			song_url = base_url + song
			request = urllib2.Request(song_url)
			request.add_header("Authorization", "Bearer " + self.client_access_token)   
			request.add_header("User-Agent", "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)") #Must include user agent of some sort, otherwise 403 returned
			try:
				response = urllib2.urlopen(request, timeout=4)
				raw = response.read()
			except socket.timeout:
				print("Timeout raised and caught")
			else:
				json_obj = json.loads(raw)
				path = json_obj["response"]["song"]["path"]
				page_url = "http://genius.com" + path
				page = requests.get(page_url)
				html = BeautifulSoup(page.text, "html.parser")
				[h.extract() for h in html('script')]
				new_lyrics = html.find("div", class_="lyrics").get_text()
				lyrics.append(new_lyrics)
		return lyrics

	def write_lyrics_file(self,lyrics):
		# write_lyrics_file
		# method to write the list of lyrics to a txt file
		output_file = open(self.output_file, 'w')
		for song in lyrics:
			output_file.write("%s\n" % song)
		output_file.close()


class LyricWriter:
	"""Lyric Writer class"""
	def __init__(self, start_word, lyrics_file, num_words):
		# init constructor for the LyricWriter class		
		self.start_word=start_word
		self.lyrics_file=lyrics_file
		self.word_count = {}
		self.word_percent = {}
		self.num_words = int(num_words)
		input_file = open(self.lyrics_file, 'r')
		input_words = re.sub("\n", " \n", input_file.read()).lower().split(' ')
		for current_word, next_word in zip(input_words[1:], input_words[:-1]):
			if current_word not in self.word_count:
				self.word_count[current_word] = {next_word: 1}
			else:
				if next_word not in self.word_count[current_word]:
					self.word_count[current_word][next_word] = 1;
				else:
					self.word_count[current_word][next_word] += 1;
		self.calc_percents()
		self.compose_lyrics()
		self.write_song_file()

	def calc_percents(self):
		# calc_percents helper method for LyricWriter init 
		# returns the next word based on a random weighted choice		
		word_percents = {}
		for current_word, current_dict in self.word_count.items():
			word_percents[current_word] = {}
			current_total = sum(current_dict.values())
			for next_word in current_dict:
				word_percents[current_word][next_word] = current_dict[next_word] / current_total
		self.word_percent = word_percents

	def get_next_word(self, curr):
		# get_next_word helper method for compose_lyrics
		# returns the next word based on a random weighted choice
		if curr not in self.word_percent:
			return random.choice(list(self.word_percent.keys()))
		else:
			word_percents = self.word_percent[curr]
			rand_percent = random.random()
			curr_percent = 0.0
			for next_word in word_percents:
				curr_percent += word_percents[next_word]
				if rand_percent <= curr_percent:
					return next_word
			return random.choice(list(self.word_percent.keys()))

	def compose_lyrics(self):
		# compose_lyrics method to compose a list of new lyrics
		# and return the results
		new_song = [self.start_word]
		for t in range(self.num_words):
			new_song.append(self.get_next_word(new_song[-1]))
		new_song = " ".join(new_song)
		self.new_lyrics = new_song


	def write_song_file(self):
		# write_song_file method to over write the input corpus txt
		# with a new list of lyrics
		output_file = open(self.lyrics_file, 'w')
		for lyric in self.new_lyrics:
			output_file.write("%s" % lyric)
		output_file.close()


def main():
	# fetch args
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--credentials', help='Path to the credentials file')
	parser.add_argument('-a', '--artist', help='Name of the artist')
	parser.add_argument('-o', '--output', help='Path to the output file')
	parser.add_argument('-s', '--start', help='Start word')
	parser.add_argument('-n', '--number', help='Number of words')

	args = parser.parse_args()

	# set defaults
	if not args.credentials:
		args.credentials = 'credentials-file.txt'
	if not args.artist:
		args.artist = 'joan of arc'
	if not args.output:
		args.output = 'lyrics.txt'
	if not args.start:
		args.start = 'eggs'
	if not args.number:
		args.number = 100		

	# scrap Genius site for all the lyrics of a given artist
	myScraper=LyricScraper(args.credentials,args.output)
	artist_id=myScraper.get_artist_id(args.artist)
	api_paths=myScraper.get_artists_songs(artist_id)
	lyrics=myScraper.get_lyrics(api_paths)
	myScraper.write_lyrics_file(lyrics)
	
	# write new lyrics using Markov chain analysis
	LyricWriter(args.start,args.output,args.number)


if __name__ == '__main__':
	main()
