# 
#  Copyright (c) 2013-present, Anoop Kunchukuttan
#  All rights reserved.
#  
#  This source code is licensed under the MIT license found in the
#  LICENSE file in the root directory of this source tree.
# 

#Program for sentence splitting of Indian language input 
#
# @author Anoop Kunchukuttan 
#
"""
Sentence splitter for Indian languages. Contains a rule-based 
sentence splitter that can understand common non-breaking phrases
in many Indian languages.
"""

import re

from indicnlp.transliterate import unicode_transliterate
from indicnlp import langinfo


## for language which have danda as delimiter
## period is not part of the sentence delimiters
DELIM_PAT_DANDA=re.compile(r'[\?!\u0964\u0965]')

## for languages which don't have danda as delimiter
DELIM_PAT_NO_DANDA=re.compile(r'[\.\?!\u0964\u0965]')

## for PersoArabic languages
DELIM_PAT_URDU=re.compile(r'[۔؟!\?]')
# Note: Languages like Sindhi, Parsi, Arabic uses normal dot instead of ۔

## pattern to check for presence of danda in text 
CONTAINS_DANDA=re.compile(r'[\u0964\u0965]')

def is_acronym_abbvr(text,lang):
    """Is the text a non-breaking phrase

    Args:
        text (str): text to check for non-breaking phrase
        lang (str): ISO 639-2 language code

    Returns:
        boolean: true if `text` is a non-breaking phrase
    """

    if lang == 'en':
        return is_en_acronym_abbvr(text)

    ack_chars =  {
     ## acronym for latin characters
      'ए', 'ऎ',
      'बी', 'बि', 
      'सी', 'सि',
      'डी', 'डि',
      'ई', 'इ',
       'एफ', 'ऎफ',
      'जी', 'जि',
      'एच','ऎच',
      'आई',  'आइ','ऐ',
      'जे', 'जॆ',
      'के', 'कॆ',
      'एल', 'ऎल',
      'एम','ऎम',
      'एन','ऎन',
      'ओ', 'ऒ',
      'पी', 'पि',
      'क्यू', 'क्यु',
      'आर', 
      'एस','ऎस',
      'टी', 'टि',
      'यू', 'यु',
      'वी', 'वि', 'व्ही', 'व्हि',
      'डब्ल्यू', 'डब्ल्यु',
      'एक्स','ऎक्स',
      'वाय',
      'जेड', 'ज़ेड',
    ##  add halant to the previous English character mappings.            
     'एफ्',
     'ऎफ्',
     'एच्',
     'ऎच्',
     'एल्',
     'ऎल्',
     'एम्',
     'ऎम्',
     'एन्',
     'ऎन्',
     'आर्',
     'एस्',
     'ऎस्',
     'एक्स्',
     'ऎक्स्',
     'वाय्',
     'जेड्', 'ज़ेड्',    

    #Indic vowels
        'ऄ',
        'अ',
        'आ',
        'इ',
        'ई',
        'उ',
        'ऊ',
        'ऋ',
        'ऌ',
        'ऍ',
        'ऎ',
        'ए',
        'ऐ',
        'ऑ',
        'ऒ',
        'ओ',
        'औ',
        'ॠ',
        'ॡ',
        
    #Indic consonants
        'क',
        'ख',
        'ग',
        'घ',
        'ङ',
        'च',
        'छ',
        'ज',
        'झ',
        'ञ',
        'ट',
        'ठ',
        'ड',
        'ढ',
        'ण',
        'त',
        'थ',
        'द',
        'ध',
        'न',
        'ऩ',
        'प',
        'फ',
        'ब',
        'भ',
        'म',
        'य',
        'र',
        'ऱ',
        'ल',
        'ळ',
        'ऴ',
        'व',
        'श',
        'ष',
        'स',
        'ह',  
        
    ## abbreviation
     'श्री',
     'डॉ',
     'कु',
     'चि',
     'सौ',
    }

    return unicode_transliterate.UnicodeIndicTransliterator.transliterate(text,lang,'hi') in ack_chars

def is_en_acronym_abbvr(text):
    """Is the English text a non-breaking phrase

    Args:
        text (str): English text to check for non-breaking phrase

    Returns:
        boolean: true if `text` is a non-breaking phrase
    """
    
    en_acr_chars = {
        
        # Latin letters used in acronyms
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
        
        # Abbrevations (American styled)
        # TODO: Add more
        'Mr', 'Ms', 'Mrs', 'Dr', 'Jr',
        'Hon', 'Prof', 'Capt', 'St',
        
        # Latin Abbrevations
        'No', # Short-form for number
        # 'viz', 'etc', 'cf

        # Currencies
        'Rs',
    }
    
    return text in en_acr_chars

def sentence_split(text,lang,delim_pat='auto'): ## New signature
    """split the text into sentences

    A rule-based sentence splitter for Indian languages written in 
    Brahmi-derived scripts. The text is split at sentence delimiter 
    boundaries. The delimiters can be configured by passing appropriate
    parameters. 

    The sentence splitter can identify non-breaking phrases like 
    single letter, common abbreviations/honorofics for some Indian 
    languages.

    Args:
        text (str): text to split into sentence
        lang (str): ISO 639-2 language code
        delim_pat (str): regular expression to identify sentence delimiter characters. If set to 'auto', the delimiter pattern is chosen automatically based on the language and text. 


    Returns:
        list: list of sentences identified from the input text 
    """
    
    #print('Input: {}'.format(delim_pat))
    if delim_pat=='auto':
        if langinfo.is_danda_delim(lang):
            # in modern texts it is possible that period is used as delimeter
            # instead of DANDA. Hence, a check. Use danda delimiter pattern
            # only if text contains at least one danda
            if CONTAINS_DANDA.search(text) is None:
                delim_pat=DELIM_PAT_NO_DANDA
                #print('LANG has danda delim. TEXT_CONTAINS_DANDA: FALSE --> DELIM_PAT_NO_DANDA')
            else:
                delim_pat=DELIM_PAT_DANDA
                #print('LANG has danda delim. TEXT_CONTAINS_DANDA: TRUE --> DELIM_PAT_DANDA')
        else:
            if lang in {'ur','pnb','ks'}:
                delim_pat=DELIM_PAT_URDU
            else:
                delim_pat=DELIM_PAT_NO_DANDA
            #print('LANG has no danda delim --> DELIM_PAT_NO_DANDA')

    ## otherwise, assume the caller set the delimiter pattern
    
    ### Phase 1: break on sentence delimiters.
    cand_sentences=[]
    begin=0
    text = text.replace('\r', '').strip()

    double_quotes_indices = []
    for i, c in enumerate(text):
        if c == '"':
            double_quotes_indices.append(i)
    
    check_for_double_quotes = False # Double-quotes aware sentence splitting
    if double_quotes_indices:
        if len(double_quotes_indices) % 2 == 0:
            check_for_double_quotes = True
        # else:
        #     print("WARNING: Unbalanced double quotes", file=sys.stderr)

    for mo in delim_pat.finditer(text):
        p1=mo.start()
        # p2=mo.end()
        
        ## Check if it's a numeric decimal point
        if text[p1] == '.' and (p1>0 and text[p1-1].isnumeric()) and (p1+1 < len(text) and text[p1+1].isnumeric()):
            continue
        
        ## Leave sentences inside double quotes as it is
        if check_for_double_quotes:
            is_quotes_open = sum([1 for i in double_quotes_indices if i < p1]) % 2
            if is_quotes_open:
                continue

        end = p1 + 1
        s = text[begin:end].strip()
        if len(s)>0:
            if len(s) == 1:
                if not cand_sentences:
                    cand_sentences.append('')
                cand_sentences[-1] += s
            else:
                cand_sentences.append(s)
        begin=p1+1

    s= text[begin:].strip()
    if len(s)>0: # Remaining chunk as new sentence
        if len(s) == 1:
            cand_sentences[-1] += s
        else:
            cand_sentences.append(s)
    
    cand_sentences_new = []
    for sentence in cand_sentences:
        cand_sentences_new.extend(sentence.split('\n'))
    cand_sentences = cand_sentences_new

    if not delim_pat.search('.'):
        ## run phase 2 only if delimiter pattern contains period
        #print('No need to run phase2')
        return cand_sentences
#     print(cand_sentences)
#     print('====')
        
#     return cand_sentences

    ### Phase 2: Address the fact that '.' may not always be a sentence delimiter
    ### Method: If there is a run of lines containing only a word (optionally) and '.',
    ### merge these lines as well one sentence preceding and succeeding this run of lines.
    final_sentences=[]
    sen_buffer=''        
    bad_state=False

    for i, sentence in enumerate(cand_sentences): 
        words=sentence.split(' ')
        #if len(words)<=2 and words[-1]=='.':
        if len(words)==1 and sentence[-1]=='.':
            bad_state=True
            sen_buffer = sen_buffer + ' ' + sentence
        ## NEW condition    
        elif sentence[-1]=='.' and is_acronym_abbvr(words[-1][:-1],lang):
            if len(sen_buffer)>0 and  not bad_state:
                final_sentences.append(sen_buffer)
            bad_state=True
            sen_buffer = sentence
        elif bad_state:
            sen_buffer = sen_buffer + ' ' + sentence
            if len(sen_buffer)>0:
                final_sentences.append(sen_buffer)
            sen_buffer=''
            bad_state=False
        else: ## good state                    
            if len(sen_buffer)>0:
                final_sentences.append(sen_buffer)
            sen_buffer=sentence
            bad_state=False

    if len(sen_buffer)>0:
        final_sentences.append(sen_buffer)
    
    return final_sentences
