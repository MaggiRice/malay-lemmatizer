#libraries to set up
from flask import Flask, render_template, request, url_for
import pickle
from malaya.dictionary import is_english
from malaya.text.function import PUNCTUATION, case_of, is_emoji
from malaya.text.regex import _expressions, _money, _date, _number
from malaya.preprocessing import Tokenizer
from herpetologist import check_type
import malaya.dictionary as dbp
import re

app = Flask(__name__, template_folder='./template')

from translate import Translator
translator= Translator(to_lang="ms")
word_list = []
unknown = []
import json
shortened_forms = json.load(open("dictionary.json"))

def map_shortened_form(word):
    if word in shortened_forms:
        return shortened_forms[word]
    else:
        unknown.append(word)
        return word


class Base:
    _tokenizer = Tokenizer().tokenize

    @check_type
    def stem(self, string: str, **kwargs):
        result = []
        tokenized = self._tokenizer(string)
        
        for no, word in enumerate(tokenized):
            if word in PUNCTUATION:
                result.append(word)
            elif (re.findall(_money, word)
                or re.findall(_date, word)
                or re.findall(_number, word)
                or re.findall(_expressions['email'], word)
                or re.findall(_expressions['url'], word)
                or re.findall(_expressions['hashtag'], word)
                or re.findall(_expressions['phone'], word)
                or re.findall(_expressions['money'], word)
                or re.findall(_expressions['date'], word)
                or re.findall(_expressions['time'], word)
                or re.findall(_expressions['ic'], word)
                or re.findall(_expressions['user'], word)  
                or is_emoji(word)
            ):
                result.append(word)
            elif is_english(word):
                result.append(translator.translate(word))
                
            elif not dbp.keyword_dbp(self.stem_word(word, **kwargs)):      
                word_list.append(word)                               
                result.append(map_shortened_form(word))
            else:
                result.append(case_of(word)(self.stem_word(word, **kwargs)))
                
        return ' '.join(result)

class Sastrawi(Base):
    def __init__(self, factory):
        self.sastrawi_stemmer = factory.create_stemmer()

    @check_type
    def stem_word(self, word: str, **kwargs):
        return self.sastrawi_stemmer.stem(word)

    @check_type
    def stem(self, string: str):
        return super().stem(string)


@check_type
def sastrawi():
    try:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    except BaseException:
        raise ModuleNotFoundError(
            'PySastrawi not installed. Please install it by `pip install PySastrawi` and try again.'
        )
    return Sastrawi(StemmerFactory())


model = sastrawi()

# routes
@app.route("/", methods=['GET', 'POST'])
def main():
    #if there if a post request
    if request.method == 'POST':
        text = request.form['malay_sentence']
        ans = model.stem(text)
            
        return render_template("./index.html", prediction = ans)

    #else just render the page
    return render_template("./index.html")

@app.route("/update", methods=['GET', 'POST'])
def update():
    ans = []
    i = 0
    global unknown
    unknown = list(set(unknown)) #remove duplicates
    #if there if a post request
    if request.method == 'POST':
        for word in unknown:
            if request.form.get(word) == "":
                break
            ans.append(request.form.get(word))
            shortened_forms[word] = ans[i]
            i += 1
        unknown = []
        json.dump(shortened_forms, open("dictionary.json", "w"), indent = 1)
        return render_template("./update.html", resopnd = "Updated!")

    #else just render the page
    return render_template("./update.html", unknown = unknown)

if __name__ =='__main__':
	app.run(debug = False)