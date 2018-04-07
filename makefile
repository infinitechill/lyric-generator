#infinite chill / 2017
all: clean lyric-generator

lyric-generator: lyric-generator.py
	cp lyric-generator.py lyric-generator
	chmod u+x lyric-generator

run:
	./lyric-generator -a 'joan of arc' -c credentials-file.txt -o newsong.txt -s bacon -n 50

clean:
	rm -f lyric-generator lyrics.txt
