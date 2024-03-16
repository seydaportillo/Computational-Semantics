#13 
#Create a function that prints the hyponyms for each of the verb synsets of a word of choice in your language of choice. 
#Use it to explore the hyponyms of 3-4 verbs in your language.

import nltk
from nltk.corpus import wordnet as wn

nltk.download('punkt')
nltk.download('wordnet')

def print_verb_hyponyms(word):
    verb_synsets = wn.synsets(word, pos=wn.VERB, lang='eng')
    
    if not verb_synsets:
        print(f"No verb synsets found for '{word}'")
        return

    for synset in verb_synsets:
        hyponyms = synset.hyponyms()
        if hyponyms:
            print(f"Hyponyms for '{synset.name()}':")
            for hyponym in hyponyms:
                print(f"- {hyponym.name()}")
        else:
            print(f"No hyponyms found for '{synset.name()}'")

print_verb_hyponyms('study')
print()

print_verb_hyponyms('play')
print()

print_verb_hyponyms('tie')
print()

#14 [Optional for oranges.] Do code that reproduces (approximately) Figure 23.5 from Jurafsky and Martin.
#15 Do code that extracts the lexical relations for the words in Figure 23.3 (e.g., that meal.n.01 is a hypernym of breakfast.n.01).
#
#I couldnt figure out how to do this.

