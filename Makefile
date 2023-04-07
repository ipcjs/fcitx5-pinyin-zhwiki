VERSION=20230320
WEB_SLANG_VERSION=20230329
FILENAME=zhwiki-$(VERSION)-all-titles-in-ns0
WEB_SLANG_FILE=web-slang-$(WEB_SLANG_VERSION).txt
WEB_SLANG_SOURCE=web-slang-$(WEB_SLANG_VERSION).source

all: build

# build: zhwiki.dict
build: zhwiki.dict.yaml

download: $(FILENAME).gz

$(FILENAME).gz:
	wget https://dumps.wikimedia.org/zhwiki/$(VERSION)/$(FILENAME).gz

$(WEB_SLANG_SOURCE):
	./zhwiki-web-slang.py --fetch > $(WEB_SLANG_SOURCE)

$(WEB_SLANG_FILE): $(WEB_SLANG_SOURCE)
	./zhwiki-web-slang.py --process $(WEB_SLANG_SOURCE) > $(WEB_SLANG_FILE)

$(FILENAME): $(FILENAME).gz
	gzip -k -d $(FILENAME).gz

zhwiki.source: $(FILENAME) $(WEB_SLANG_FILE)
	cat $(FILENAME) $(WEB_SLANG_FILE) > zhwiki.source

zhwiki.raw: zhwiki.source
	./convert.py zhwiki.source > zhwiki.raw.tmp
	sort -u zhwiki.raw.tmp > zhwiki.raw

zhwiki.dict: zhwiki.raw
	libime_pinyindict zhwiki.raw zhwiki.dict

zhwiki.dict.yaml: zhwiki.source
	echo '# VERSION: $(VERSION)' > zhwiki.dict.yaml
	echo '# WEB_SLANG_VERSION: $(WEB_SLANG_VERSION)' >> zhwiki.dict.yaml
	echo '---\nname: zhwiki\nversion: "0.1"\nsort: by_weight\n...\n' >> zhwiki.dict.yaml
	./convert.py zhwiki.source --rime >> zhwiki.dict.yaml

install: zhwiki.dict
	install -Dm644 zhwiki.dict -t $(DESTDIR)/usr/share/fcitx5/pinyin/dictionaries/

install_rime_dict: zhwiki.dict.yaml
	install -Dm644 zhwiki.dict.yaml -t $(DESTDIR)/usr/share/rime-data/

clean:
	rm -f $(FILENAME) $(WEB_SLANG_FILE) zhwiki.source zhwiki.raw zhwiki.dict zhwiki.dict.yaml
