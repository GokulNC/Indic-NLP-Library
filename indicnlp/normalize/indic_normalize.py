# -*- coding: utf-8 -*-

# 
#  Copyright (c) 2013-present, Anoop Kunchukuttan
#  All rights reserved.
#  
#  This source code is licensed under the MIT license found in the
#  LICENSE file in the root directory of this source tree.
# 

#Program for normalization of text written in Unicode. This is mainly geared towards Indic scripts 
#
# @author Anoop Kunchukuttan 
#

import sys, codecs, string, itertools, re
from indicnlp import langinfo


class NormalizerI(object):
    """
    The normalizer classes do the following: 

    * Some characters have multiple Unicode codepoints. The normalizer chooses a single standard representation
    * Some control characters are deleted
    * While typing using the Latin keyboard, certain typical mistakes occur which are corrected by the module

    Base class for normalizer. Performs some common normalization, which includes: 

    * Byte order mark, word joiner, etc. removal 
    * ZERO_WIDTH_NON_JOINER and ZERO_WIDTH_JOINER removal 
    * ZERO_WIDTH_SPACE and NO_BREAK_SPACE replaced by spaces 

    Script specific normalizers should derive from this class and override the normalize() method. 
    They can call the super class 'normalize() method to avail of the common normalization 

    """

    BYTE_ORDER_MARK='\uFEFF'
    BYTE_ORDER_MARK_2='\uFFFE'
    WORD_JOINER='\u2060'
    SOFT_HYPHEN='\u00AD'

    ZERO_WIDTH_SPACE='\u200B'
    NO_BREAK_SPACE='\u00A0'

    ZERO_WIDTH_NON_JOINER='\u200C'
    ZERO_WIDTH_JOINER='\u200D'

    def _normalize_punctuations(self, text):
        """
        Normalize punctuations. 
        Applied many of the punctuation normalizations that are part of MosesNormalizer 
        from sacremoses
        """
        text=text.replace(NormalizerI.BYTE_ORDER_MARK,'')
        text=text.replace('„', r'"')
        text=text.replace('“', r'"')
        text=text.replace('”', r'"')
        text=text.replace('–', r'-')
        text=text.replace('—', r' - ')
        text=text.replace('´', r"'")
        text=text.replace('‘', r"'")
        text=text.replace('‚', r"'")
        text=text.replace('’', r"'")
        text=text.replace("''", r'"')
        text=text.replace('´´', r'"')
        text=text.replace('…', r'...')

        return text

    def normalize(self,text):
        pass 


class BaseNormalizer(NormalizerI):

    def __init__(self,lang,
            remove_nuktas=False,
            decompose_nuktas=False,
            nasals_mode='do_nothing',
            do_normalize_chandras=False,
            do_normalize_vowel_ending=False,
            do_normalize_numerals=False,
            convert_numerals_to_native=False,
            do_colon_to_visarga=False):

        self.lang=lang
        self.remove_nuktas=remove_nuktas
        self.decompose_nuktas = decompose_nuktas
        self.nasals_mode=nasals_mode
        self.do_normalize_chandras=do_normalize_chandras
        self.do_normalize_vowel_ending=do_normalize_vowel_ending
        self.do_normalize_numerals=do_normalize_numerals
        self.convert_numerals_to_native=convert_numerals_to_native
        self.do_colon_to_visarga=do_colon_to_visarga
        # TODO: Make visarga correction generic
        
        self._init_normalize_chandras()
        self._init_normalize_nasals()
        self._init_normalize_vowel_ending()
        self._init_normalize_numerals()
        #self._init_visarga_correction()
    
    def _init_normalize_numerals(self):
        native_to_hindu_numerals_map={}
        hindu_numerals_to_native_map={}
        for i in range(10):
            native_digit=langinfo.offset_to_char(langinfo.NUMERIC_OFFSET_START+i,self.lang)
            native_to_hindu_numerals_map[native_digit]=str(i)
            hindu_numerals_to_native_map[str(i)]=native_digit
        self.native_to_hindu_numerals_translator=str.maketrans(native_to_hindu_numerals_map)
        self.hindu_numerals_to_native_translator=str.maketrans(hindu_numerals_to_native_map)
        
    def _init_normalize_vowel_ending(self):

        if self.lang in langinfo.IE_LANGUAGES:
            self.fn_vowel_ending=self._normalize_word_vowel_ending_ie
        elif self.lang in langinfo.DRAVIDIAN_LANGUAGES:
            self.fn_vowel_ending=self._normalize_word_vowel_ending_dravidian
        else:
            self.fn_vowel_ending=lambda x: x

    def _init_normalize_chandras(self):

        substitution_offsets =\
            [
                [0x0d , 0x0f], # chandra e, independent
                [0x11 , 0x13], # chandra o, independent
                [0x45 , 0x47], # chandra e , 0xde],pendent
                [0x49 , 0x4b], # chandra o , 0xde],pendent
                # [0x72 , 0x0f], # mr: chandra e, independent

                [0x00 , 0x02], # chandrabindu
                [0x01 , 0x02], # chandrabindu
            ]

        self.chandra_substitutions =  [ 
                (langinfo.offset_to_char(x[0],self.lang), langinfo.offset_to_char(x[1],self.lang)) 
                    for x in substitution_offsets ]

    def _normalize_chandras(self,text):
        for match, repl in self.chandra_substitutions:
            text=text.replace(match,repl)
        return text

    def _init_to_anusvaara_strict(self):
        """
        `r1_nasal=re.compile(r'\\u0919\\u094D([\\u0915-\\u0918])')`
        """
    
        pat_signatures=\
            [
                 [0x19,0x15,0x18],
                 [0x1e,0x1a,0x1d],            
                 [0x23,0x1f,0x22],                        
                 [0x28,0x24,0x27],        
                 [0x29,0x24,0x27],                    
                 [0x2e,0x2a,0x2d],                    
            ]    
        
        halant_offset=0x4d
        anusvaara_offset=0x02
        
        pats=[]
        
        for pat_signature in pat_signatures:
            pat=re.compile(r'{nasal}{halant}([{start_r}-{end_r}])'.format(
                nasal=langinfo.offset_to_char(pat_signature[0],self.lang),
                halant=langinfo.offset_to_char(halant_offset,self.lang),
                start_r=langinfo.offset_to_char(pat_signature[1],self.lang),
                end_r=langinfo.offset_to_char(pat_signature[2],self.lang),
            ))
            pats.append(pat)
        
        repl_string='{anusvaara}\\1'.format(anusvaara=langinfo.offset_to_char(anusvaara_offset,self.lang))

        self.pats_repls=(pats,repl_string)
    
    def _to_anusvaara_strict(self,text):
        
        pats, repl_string = self.pats_repls
        for pat in pats:
            text=pat.sub(repl_string,text)
            
        return text

    def _init_to_anusvaara_relaxed(self):
        """
        `r1_nasal=re.compile(r'\\u0919\\u094D([\\u0915-\\u0918])')`
        """
            
        nasals_list=[0x19,0x1e,0x23,0x28,0x29,0x2e]    
        nasals_list_str=','.join([langinfo.offset_to_char(x,self.lang) for x in nasals_list])
        
        halant_offset=0x4d    
        anusvaara_offset=0x02    
        
        pat=re.compile(r'[{nasals_list_str}]{halant}'.format(
                nasals_list_str=nasals_list_str,
                halant=langinfo.offset_to_char(halant_offset,self.lang),
            ))
        
        repl_string='{anusvaara}'.format(anusvaara=langinfo.offset_to_char(anusvaara_offset,self.lang))

        self.pats_repls = (pat,repl_string)
    
    def _to_anusvaara_relaxed(self,text):
        pat, repl_string = self.pats_repls
        return pat.sub(repl_string,text)
    

    def _init_to_nasal_consonants(self):
        """
        `r1_nasal=re.compile(r'\\u0919\\u094D([\\u0915-\\u0918])')`
        """
    
        pat_signatures=\
            [
                 [0x19,0x15,0x18],
                 [0x1e,0x1a,0x1d],            
                 [0x23,0x1f,0x22],                        
                 [0x28,0x24,0x27],        
                 [0x29,0x24,0x27],                    
                 [0x2e,0x2a,0x2d],                    
            ]    
        
        halant_offset=0x4d
        anusvaara_offset=0x02 
        
        pats=[]
        repl_strings=[]
        
        for pat_signature in pat_signatures:
            pat=re.compile(r'{anusvaara}([{start_r}-{end_r}])'.format(
                anusvaara=langinfo.offset_to_char(anusvaara_offset,self.lang),
                start_r=langinfo.offset_to_char(pat_signature[1],self.lang),
                end_r=langinfo.offset_to_char(pat_signature[2],self.lang),
            ))
            pats.append(pat)
            repl_string='{nasal}{halant}\\1'.format(
                nasal=langinfo.offset_to_char(pat_signature[0],self.lang),
                halant=langinfo.offset_to_char(halant_offset,self.lang),
                )
            repl_strings.append(repl_string)
    
        self.pats_repls=list(zip(pats,repl_strings))

    def _to_nasal_consonants(self,text):
    
        for pat, repl in self.pats_repls:
            text=pat.sub(repl,text)
            
        return text

    def _init_normalize_nasals(self):

        if self.nasals_mode == 'to_anusvaara_strict':
            self._init_to_anusvaara_strict()
        elif self.nasals_mode == 'to_anusvaara_relaxed':
            self._init_to_anusvaara_relaxed()
        elif self.nasals_mode == 'to_nasal_consonants':
            self._init_to_nasal_consonants()

    def _normalize_nasals(self,text): 
        if self.nasals_mode == 'to_anusvaara_strict':
            return self._to_anusvaara_strict(text)
        elif self.nasals_mode == 'to_anusvaara_relaxed':
            return self._to_anusvaara_relaxed(text)
        elif self.nasals_mode == 'to_nasal_consonants':
            return self._to_nasal_consonants(text)
        else:
            return text

    
    def _normalize_word_vowel_ending_dravidian(self,word):
        """
        for Dravidian
        - consonant ending: add 'a' ki maatra
        - halant ending: no change
        - 'a' ki maatra: no change
        """
        if len(word)>0 and langinfo.is_consonant(word[-1],self.lang):
            return word+langinfo.offset_to_char(0x3e,self.lang)
        else:
            return word

    def _normalize_word_vowel_ending_ie(self,word):
        """
        for IE
        - consonant ending: add halant
        - halant ending: no change
        - 'a' ki maatra: no change
        """
        if len(word)>0 and langinfo.is_consonant(word[-1],self.lang):
            return word+langinfo.offset_to_char(langinfo.HALANTA_OFFSET,self.lang)
        else:
            return word 

    def _normalize_vowel_ending(self,text):
        return ' '.join([ self.fn_vowel_ending(w) for w in text.split(' ') ])

    def normalize(self,text):
        """
        Method to be implemented for normalization for each script 
        """
        text=text.replace(NormalizerI.BYTE_ORDER_MARK,'')
        text=text.replace(NormalizerI.BYTE_ORDER_MARK_2,'')
        text=text.replace(NormalizerI.WORD_JOINER,'')
        text=text.replace(NormalizerI.SOFT_HYPHEN,'')

        text=text.replace(NormalizerI.ZERO_WIDTH_SPACE,' ') # ??
        text=text.replace(NormalizerI.NO_BREAK_SPACE,' ')

        text=text.replace(NormalizerI.ZERO_WIDTH_NON_JOINER, '')
        text=text.replace(NormalizerI.ZERO_WIDTH_JOINER,'')
        
        text=self._normalize_punctuations(text)

        if self.do_normalize_chandras:
            text=self._normalize_chandras(text)
        text=self._normalize_nasals(text)
        if self.do_normalize_vowel_ending:
            text=self._normalize_vowel_ending(text)
        
        if self.do_normalize_numerals:
            text=text.translate(self.native_to_hindu_numerals_translator)
        elif self.convert_numerals_to_native:
            text=text.translate(self.hindu_numerals_to_native_translator)
        
        return text


    def get_char_stats(self,text):    
        print(len(re.findall(NormalizerI.BYTE_ORDER_MARK,text)))
        print(len(re.findall(NormalizerI.BYTE_ORDER_MARK_2,text)))
        print(len(re.findall(NormalizerI.WORD_JOINER,text)))
        print(len(re.findall(NormalizerI.SOFT_HYPHEN,text)))

        print(len(re.findall(NormalizerI.ZERO_WIDTH_SPACE,text) ))
        print(len(re.findall(NormalizerI.NO_BREAK_SPACE,text)))

        print(len(re.findall(NormalizerI.ZERO_WIDTH_NON_JOINER,text)))
        print(len(re.findall(NormalizerI.ZERO_WIDTH_JOINER,text)))

        #for mobj in re.finditer(NormalizerI.ZERO_WIDTH_NON_JOINER,text):
        #    print text[mobj.start()-10:mobj.end()+10].replace('\n', ' ').replace(NormalizerI.ZERO_WIDTH_NON_JOINER,'').encode('utf-8')
        #print hex(ord(text[mobj.end():mobj.end()+1]))

    def correct_visarga(self,text,visarga_char,char_range):
        text=re.sub(r'([\u0900-\u097f]):','\\1\u0903',text)
        


class DevanagariNormalizer(BaseNormalizer): 
    """
    Normalizer for the Devanagari script. In addition to basic normalization by the super class, 

    * Replaces the composite characters containing nuktas by their decomposed form 
    * replace pipe character '|' by poorna virama character
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    
    """

    NUKTA='\u093C' 

    def __init__(self,lang='hi',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
            do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False):
        super(DevanagariNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)

    def _normalize_vowels(self,text):
        # Two-part vowels
        text=text.replace("\u093e\u093a","\u093b") # ा + ऺ ->  ऻ 
        text=text.replace("\u093e\u0945","\u0949") # ा + ॅ ->  ॉ 
        text=text.replace("\u093e\u0946","\u094a") # ा + ॆ ->  ॊ 
        text=text.replace("\u093e\u0947","\u094b") # ा + े ->  ो 
        text=text.replace("\u093e\u0948","\u094c") # ा + ै ->  ौ 

        # # chandra a replacement for Marathi
        # text=text.replace('\u0972','\u090f')
        return text

    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(DevanagariNormalizer,self).normalize(text)
        text=self._normalize_vowels(text)

        if self.remove_nuktas:

            text=text.replace(DevanagariNormalizer.NUKTA,'')
            # normalize Nukta based composite characters
            text=text.replace('\u0929','\u0928')
            text=text.replace('\u0931','\u0930')
            text=text.replace('\u0934','\u0933')
            text=text.replace('\u0958','\u0915')
            text=text.replace('\u0959','\u0916')
            text=text.replace('\u095A','\u0917')
            text=text.replace('\u095B','\u091C')
            text=text.replace('\u095C','\u0921')
            text=text.replace('\u095D','\u0922')
            text=text.replace('\u095E','\u092B')
            text=text.replace('\u095F','\u092F')
        
        else:
            if self.decompose_nuktas:
                # decomposing Nukta based composite characters
                text=text.replace('\u0929','\u0928'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u0931','\u0930'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u0934','\u0933'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u0958','\u0915'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u0959','\u0916'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095A','\u0917'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095B','\u091C'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095C','\u0921'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095D','\u0922'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095E','\u092B'+DevanagariNormalizer.NUKTA)
                text=text.replace('\u095F','\u092F'+DevanagariNormalizer.NUKTA)
            else:
                # recomposing Nukta based composite characters
                # Warning: Might increase your vocab size a litte bit
                text=text.replace('\u0928'+DevanagariNormalizer.NUKTA, '\u0929')
                text=text.replace('\u0930'+DevanagariNormalizer.NUKTA, '\u0931')
                text=text.replace('\u0933'+DevanagariNormalizer.NUKTA, '\u0934')
                text=text.replace('\u0915'+DevanagariNormalizer.NUKTA, '\u0958')
                text=text.replace('\u0916'+DevanagariNormalizer.NUKTA, '\u0959')
                text=text.replace('\u0917'+DevanagariNormalizer.NUKTA, '\u095A')
                text=text.replace('\u091C'+DevanagariNormalizer.NUKTA, '\u095B')
                text=text.replace('\u0921'+DevanagariNormalizer.NUKTA, '\u095C')
                text=text.replace('\u0922'+DevanagariNormalizer.NUKTA, '\u095D')
                text=text.replace('\u092B'+DevanagariNormalizer.NUKTA, '\u095E')
                text=text.replace('\u092F'+DevanagariNormalizer.NUKTA, '\u095F')

        # replace pipe character for poorna virama 
        text=text.replace('\u007c','\u0964')

        if self.do_colon_to_visarga: # correct visarga 
            text=re.sub(r'([\u0900-\u097f]):','\\1\u0903',text)

        return text

    def get_char_stats(self,text):
        super(DevanagariNormalizer,self).get_char_stats(text)

        print((len(re.findall('\u0929',text))))
        print((len(re.findall('\u0931',text))))
        print((len(re.findall('\u0934',text))))
        print((len(re.findall('\u0958',text))))
        print((len(re.findall('\u0959',text))))
        print((len(re.findall('\u095A',text))))
        print((len(re.findall('\u095B',text))))
        print((len(re.findall('\u095C',text))))
        print((len(re.findall('\u095D',text))))
        print((len(re.findall('\u095E',text))))
        print((len(re.findall('\u095F',text))))

        #print(len(re.findall(u'\u0928'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0930'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0933'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0915'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0916'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0917'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u091C'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0921'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u0922'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u092B'+DevanagariNormalizer.NUKTA,text)))
        #print(len(re.findall(u'\u092F'+DevanagariNormalizer.NUKTA,text)))

class KashmiriDevanagariNormalizer(DevanagariNormalizer):
    '''
    Refer for orthographic changes: https://r12a.github.io/scripts/devanagari/kashmiri#previousOrthographies
    '''

    def __init__(self,lang='ks_IN',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
            do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
            do_convert_1995_to_2002_orthography=True,do_convert_vowels_with_apostrophe_to_short=False,
            do_convert_2002_to_2009_orthography=True):
        super(KashmiriDevanagariNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        if remove_nuktas:
            print("WARNING: Removing nuqtas in Kashmiri is not recommended. Proceed with caution.")
        self.do_convert_1995_to_2002_orthography=do_convert_1995_to_2002_orthography
        self.do_convert_vowels_with_apostrophe_to_short=do_convert_vowels_with_apostrophe_to_short
        self.do_convert_2002_to_2009_orthography=do_convert_2002_to_2009_orthography
    
    def _1995_to_2002_orthography(self,text,convert_vowels_with_apostrophe_to_short=False):
        # Dependent vowels
        text=text.replace("\u0941\u0945","\u0956") # ुॅ ->  ॖ 
        text=text.replace("\u0945\u0941","\u0956") # ॅु ->  ॖ 
        text=text.replace("\u0942\u0945","\u0957") # ूॅ ->  ॗ 
        text=text.replace("\u0945\u0942","\u0957") # ॅू ->  ॗ 
        text=re.sub("([\u0915-\u0939\u0958-\u095f\u093c])\u093d","\\1\u0945",text) # Consonant+ऽ -> Consonant+ॅ 
        if convert_vowels_with_apostrophe_to_short:
            text=text.replace("\u0947'","\u0946") # े' ->  ॆ 
            text=text.replace("\u094b'","\u094a") # ो' ->  ॊ 
            text=text.replace("\u094c'","\u094f") # ौ' ->  ॏ 

        # Independent vowels
        text=text.replace("\u0909\u0945","\u0976") # उॅ -> ॶ 
        text=text.replace("\u090a\u0945","\u0977") # ऊॅ -> ॷ 
        text=text.replace("\u093d","\u0972") # ऽ -> ॲ 
        if convert_vowels_with_apostrophe_to_short:
            text=text.replace("\u090f'","\u090e") # ए' -> ऎ 
            text=text.replace("\u0913'","\u0912") # ओ' -> ऒ 
            text=text.replace("\u0914'","\u0975") # औ' -> ॵ 
        
        return text
    
    def _2002_to_2009_orthography(self,text):
        # Dependent vowels
        text=text.replace("\u0945","\u093a") # ॅ ->  ऺ 
        text=text.replace("\u0949","\u093b") # ॉ ->  ऻ 
        text=re.sub("\u094d\u0935([^\u093a-\u0957])","\u094f\\1",text) # ्व ->  ॏ 

        # Independent vowels
        text=text.replace("\u0972","\u0973") # ॲ -> ॳ 
        text=text.replace("\u0911","\u0974") # ऑ -> ॴ 

        return text

    def normalize(self,text):
        # common normalization for Devanagari 
        text=super(KashmiriDevanagariNormalizer,self).normalize(text)
        if self.do_convert_1995_to_2002_orthography:
            text=self._1995_to_2002_orthography(text,self.do_convert_vowels_with_apostrophe_to_short)
        if self.do_convert_2002_to_2009_orthography:
            text=self._2002_to_2009_orthography(text)
        return text

class SanskritNormalizer(DevanagariNormalizer):
    '''
    On top of Devanagari normalizer, implements Sanskrit-specific features:
    - Drop Vedic Tone Accent marks
    - [Experimental] Sandhi splitter using: https://github.com/kmadathil/sanskrit_parser
      - Very time-consuming, recommended to run using multiprocessing
    '''

    def __init__(self,lang='sa',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
            do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=True,do_colon_to_visarga=True,
            do_drop_accent=True,do_split_sandhi=False,do_cache_sandhi=True):
        super(SanskritNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.do_drop_accent = do_drop_accent
        self.do_split_sandhi = do_split_sandhi
        if self.do_split_sandhi:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            from sanskrit_parser import Parser
            self.parser = Parser(output_encoding='Devanagari')
            self.do_cache_sandhi = do_cache_sandhi
            if self.do_cache_sandhi:
                # Sandhi-splitting implementation is combinatorial-scoring based
                # So for faster access, better to cache already seen chunks
                self.sandhi_cache = {}
    
    def normalize(self,text):
        # common normalization for Devanagari 
        text=super(SanskritNormalizer,self).normalize(text)
        if self.do_drop_accent:
            # Drop Sandhi-bridge-accent
            text = re.sub('[\u0967\u0969][\u0951\u0952]', '', text)
            # Drop all other remaining accent marks
            text = re.sub('[\u0951-\u0954\u1cd0-\u1cff\u0971]', '', text)
        
        if self.do_split_sandhi:
            # Split sentence into parts
            matches = re.findall('[\u0900-\u0963\u0972-\u097f]+', text)
            # Sandhi-split for each chunk
            for match in matches:
                if match not in self.sandhi_cache:
                    # Ref: https://github.com/kmadathil/sanskrit_parser/blob/master/examples/basic_example.ipynb
                    split_seqs = self.parser.split(match, limit=1)
                    if not split_seqs:
                        # print("Unable to find roots for:", match)
                        self.sandhi_cache[match] = match
                        continue
                    split_seq = split_seqs[0]
                    splits = [t.transcoded(split_seq.parser.output_encoding, split_seq.parser.strict_io) for t in split_seq.split]
                    self.sandhi_cache[match] = ' '.join(splits)
                
                text = text.replace(match, self.sandhi_cache[match])

        return text


class GurmukhiNormalizer(BaseNormalizer): 
    """
    Normalizer for the Gurmukhi script. In addition to basic normalization by the super class, 

    * Replaces the composite characters containing nuktas by their decomposed form 
    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * replace pipe character '|' by poorna virama character
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    NUKTA='\u0A3C' 

    VOWEL_NORM_MAPS={
        ## http://www.unicode.org/versions/Unicode12.1.0/ch12.pdf
        ## Table 12-16
        '\u0a05\u0a3e': '\u0a06',
        '\u0a72\u0a3f': '\u0a07',
        '\u0a72\u0a40': '\u0a08',
        '\u0a73\u0a41': '\u0a09',
        '\u0a73\u0a42': '\u0a0a',
        '\u0a72\u0a47': '\u0a0f',
        '\u0a05\u0a48': '\u0a10',
        '\u0a73\u0a4b': '\u0a13',
        '\u0a05\u0a4c': '\u0a14',            
    }

    def __init__(self,lang='pa',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
                do_canonicalize_addak=False, 
                do_canonicalize_tippi=False, 
                do_replace_vowel_bases=False):
        super(GurmukhiNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.do_canonicalize_addak=do_canonicalize_addak
        self.do_canonicalize_tippi=do_canonicalize_tippi
        self.do_replace_vowel_bases=do_replace_vowel_bases


    def _normalize_vowels(self,text):
        """

        """

        ## standard vowel replacements as per suggestions in 
        ## http://www.unicode.org/versions/Unicode12.1.0/ch12.pdf
        ## Table 12-16

        for k,v in GurmukhiNormalizer.VOWEL_NORM_MAPS.items():
            text=text.replace(k,v)
        
        ## the above mappings should account for majority of the variantions, 
        ## Rest are handled via this generic rule which looks at the diacritic 
        ## following the 2 special characters 
        ## TBD: don't see evidence for this in Wikipedia corpus

        ## If these special characters occur without any diacritic, replace them with closet
        ## equivalent vowels
        if self.do_replace_vowel_bases:
            text=text.replace('\u0a72','\u0a07')
            text=text.replace('\u0a73','\u0a09')

        return text


    def normalize(self,text): 

        # Addak
        if self.do_canonicalize_addak:
            ## replace addak+consonant with consonat+halant+consonant
            text=re.sub(r'\u0a71(.)','\\1\u0a4d\\1',text)
            
        # Tippi 
        if self.do_canonicalize_tippi:
            text=text.replace('\u0a70','\u0a02') 

        # Vowels: Gurumuki has multiple ways of representing independent vowels due
        # to the characters 'iri' and 'ura'. 
        text=self._normalize_vowels(text)

        # common normalization for Indic scripts 
        text=super(GurmukhiNormalizer,self).normalize(text)
        
        if self.remove_nuktas:
            text=text.replace(GurmukhiNormalizer.NUKTA,'')
            # normalizing Nukta based composite characters
            text=text.replace('\u0a33','\u0a32')
            text=text.replace('\u0a36','\u0a38')
            text=text.replace('\u0a59','\u0a16')
            text=text.replace('\u0a5a','\u0a17')
            text=text.replace('\u0a5b','\u0a1c')
            text=text.replace('\u0a5e','\u0a2b')
        else:
            if self.decompose_nuktas:
                # decomposing Nukta based composite characters
                text=text.replace('\u0a33','\u0a32'+GurmukhiNormalizer.NUKTA)
                text=text.replace('\u0a36','\u0a38'+GurmukhiNormalizer.NUKTA)
                text=text.replace('\u0a59','\u0a16'+GurmukhiNormalizer.NUKTA)
                text=text.replace('\u0a5a','\u0a17'+GurmukhiNormalizer.NUKTA)
                text=text.replace('\u0a5b','\u0a1c'+GurmukhiNormalizer.NUKTA)
                text=text.replace('\u0a5e','\u0a2b'+GurmukhiNormalizer.NUKTA)
            else:
                # recomposing Nukta based composite characters
                text=text.replace('\u0a32'+GurmukhiNormalizer.NUKTA, '\u0a33')
                text=text.replace('\u0a38'+GurmukhiNormalizer.NUKTA, '\u0a36')
                text=text.replace('\u0a16'+GurmukhiNormalizer.NUKTA, '\u0a59')
                text=text.replace('\u0a17'+GurmukhiNormalizer.NUKTA, '\u0a5a')
                text=text.replace('\u0a1c'+GurmukhiNormalizer.NUKTA, '\u0a5b')
                text=text.replace('\u0a2b'+GurmukhiNormalizer.NUKTA, '\u0a5e')

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0a64','\u0964')
        text=text.replace('\u0a65','\u0965')

        ## replace pipe character for poorna virama 
        text=text.replace('\u007c','\u0964')

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0a00-\u0a7f]):','\\1\u0a03',text)

        return text


class GujaratiNormalizer(BaseNormalizer): 
    """
    Normalizer for the Gujarati script. In addition to basic normalization by the super class, 

    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    NUKTA='\u0ABC' 

    def __init__(self,lang='gu',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                    do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False):
        super(GujaratiNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)

    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(GujaratiNormalizer,self).normalize(text)

        # decomposing Nukta based composite characters
        if self.remove_nuktas:
            text=text.replace(GujaratiNormalizer.NUKTA,'')


        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0ae4','\u0964')
        text=text.replace('\u0ae5','\u0965')

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0a80-\u0aff]):','\\1\u0a83',text)

        return text


class OriyaNormalizer(BaseNormalizer): 
    """
    Normalizer for the Oriya script. In addition to basic normalization by the super class, 

    * Replaces the composite characters containing nuktas by their decomposed form 
    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * Canonicalize two part dependent vowels
    * Replace 'va' with 'ba'
    * replace pipe character '|' by poorna virama character
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    NUKTA='\u0B3C' 

    VOWEL_NORM_MAPS={
        ## See Table 12-22 in http://www.unicode.org/versions/Unicode12.1.0/ch12.pdf
        '\u0b05\u0b3e': '\u0b06',
        '\u0b0f\u0b57': '\u0b10',
        '\u0b13\u0b57': '\u0b14',
    }


    def __init__(self,lang='or',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
                do_remap_wa=False):
        super(OriyaNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.do_remap_wa=do_remap_wa

    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(OriyaNormalizer,self).normalize(text)

        ## standard vowel replacements as per suggestions in Unicode documents
        for k,v in OriyaNormalizer.VOWEL_NORM_MAPS.items():
            text=text.replace(k,v)

        if self.remove_nuktas:
            text=text.replace(OriyaNormalizer.NUKTA,'')
            # normalizing Nukta based composite characters
            text=text.replace('\u0b5c','\u0b21')
            text=text.replace('\u0b5d','\u0b22')
        else:
            if self.decompose_nuktas:
                # decomposing Nukta based composite characters
                text=text.replace('\u0b5c','\u0b21'+OriyaNormalizer.NUKTA)
                text=text.replace('\u0b5d','\u0b22'+OriyaNormalizer.NUKTA)
            else:
                # recomposing Nukta based composite characters
                text=text.replace('\u0b21'+OriyaNormalizer.NUKTA, '\u0b5c')
                text=text.replace('\u0b22'+OriyaNormalizer.NUKTA, '\u0b5d')

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0b64','\u0964')
        text=text.replace('\u0b65','\u0965')

        # replace pipe character for poorna virama 
        text=text.replace('\u0b7c','\u0964')

        # # replace va with ba 
        # # NOTE: documentation (chapter on Indic scripts) and codepoint chart seem contradictory 
        # # (this applied to wa to ba rule also above)
        # text=text.replace('\u0b35','\u0b2c')

        # replace va with wa 
        text=text.replace('\u0b35','\u0b71')

        # replace wa with ba 
        if self.do_remap_wa:
            text=text.replace('\u0b71','\u0b2c')

        # AI dependent vowel sign 
        text=text.replace('\u0b47\u0b56','\u0b58')

        # two part dependent vowels
        text=text.replace('\u0b47\u0b3e','\u0b4b')
        text=text.replace('\u0b47\u0b57','\u0b4c')


        # additional consonant - not clear how to handle this
        # ignore

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0b00-\u0b7f]):','\\1\u0b03',text)

        return text


class BengaliNormalizer(BaseNormalizer): 
    """
    Normalizer for the Bengali script. In addition to basic normalization by the super class, 

    * Replaces the composite characters containing nuktas by their decomposed form 
    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * Canonicalize two part dependent vowels
    * replace pipe character '|' by poorna virama character
    * replace colon ':' by visarga if the colon follows a charcter in this script 

    """

    NUKTA='\u09BC' 

    def __init__(self,lang='bn',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                    do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
                    do_remap_assamese_chars=False):
        super(BengaliNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.do_remap_assamese_chars=do_remap_assamese_chars

    def normalize(self,text):

        # common normalization for Indic scripts 
        text=super(BengaliNormalizer,self).normalize(text)

        if self.remove_nuktas:
            text=text.replace(BengaliNormalizer.NUKTA,'')
            # normalizing Nukta based composite characters
            text=text.replace('\u09dc','\u09a1')
            text=text.replace('\u09dd','\u09a2')
            text=text.replace('\u09df','\u09af')
        else:
            if self.decompose_nuktas:
                # decomposing Nukta based composite characters
                text=text.replace('\u09dc','\u09a1'+BengaliNormalizer.NUKTA)
                text=text.replace('\u09dd','\u09a2'+BengaliNormalizer.NUKTA)
                text=text.replace('\u09df','\u09af'+BengaliNormalizer.NUKTA)
            else:
                # recomposing Nukta based composite characters
                text=text.replace('\u09a1'+BengaliNormalizer.NUKTA, '\u09dc')
                text=text.replace('\u09a2'+BengaliNormalizer.NUKTA, '\u09dd')
                text=text.replace('\u09af'+BengaliNormalizer.NUKTA, '\u09df')

        if self.lang=='as':
            if self.do_remap_assamese_chars:
                # Normalize Assamese chars to Bengali
                text=text.replace('\u09f0','\u09b0')  #  'ra' character
                text=text.replace('\u09f1','\u09ac')  #  'va' character to 'ba'
            else:
                text=text.replace('\u09b0','\u09f0')  #  'ra' character

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u09e4','\u0964')
        text=text.replace('\u09e5','\u0965')

        # replace pipe character for poorna virama 
        text=text.replace('\u007c','\u0964')
        # replace bengali currency numerator four for poorna virama  (it looks similar and is used as a substitute)
        text=text.replace('\u09f7','\u0964')

        # two part dependent vowels
        text=text.replace('\u09c7\u09be','\u09cb')
        text=text.replace('\u09c7\u09d7','\u09cc')

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0980-\u09ff]):','\\1\u0983',text)

        return text


class TamilNormalizer(BaseNormalizer): 
    """
    Normalizer for the Tamil script. In addition to basic normalization by the super class, 

    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * canonicalize two-part dependent vowel signs
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    def __init__(self,lang='ta',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
            do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
            normalize_grantha=False):
        super(TamilNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.normalize_grantha = normalize_grantha

    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(TamilNormalizer,self).normalize(text)

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0be4','\u0964')
        text=text.replace('\u0be5','\u0965')

        # two part dependent vowels
        text=text.replace('\u0b92\u0bd7','\u0b94')
        text=text.replace('\u0bc6\u0bbe','\u0bca')
        text=text.replace('\u0bc7\u0bbe','\u0bcb')
        text=text.replace('\u0bc6\u0bd7','\u0bcc')

        if self.remove_nuktas:
            # In Tamil, it's equivalent to removing translingual ஃ
            text=text.replace('\u0b83\u0b9c', '\u0b9c') # ஃஜ (za)
            text=text.replace('\u0b83\u0b95', '\u0b95') # ஃக (qa)
            text=text.replace('\u0b83\u0baa', '\u0baa') # ஃப (fa)
            # In other places, ஃ denotes a voiceless uvular fricative or visarga if final

        if self.normalize_grantha:
            # Convert additional grantha consonants to core Tamil
            text=text.replace('\u0bb6\u0bcd\u0bb0\u0bc0', '\u0ba4\u0bbf\u0bb0\u0bc1') # ஸ்ரீ -> திரு
            text=text.replace('\u0b9c','\u0b9a') # ஜ -> ச
            text=text.replace('\u0bb6','\u0b9a') # ஶ -> ச
            text=text.replace('\u0bb7','\u0b9a') # ஷ -> ச
            text=text.replace('\u0bb8','\u0b9a') # ஸ -> ச
            text=text.replace('\u0bb9','\u0b95') # ஹ -> க
            text=text.replace('\u0b82','\u0bae\u0bcd') # ஂ -> ம்
        
        # # Correct Indic visarge. Does not apply to Tamil, since visarga is ஃ
        # if self.do_colon_to_visarga:
        #     text=re.sub(r'([\u0b80-\u0bff]):','\\1\u0b83',text)

        return text


class TeluguNormalizer(BaseNormalizer): 
    """
    Normalizer for the Teluguscript. In addition to basic normalization by the super class, 

    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * canonicalize two-part dependent vowel signs
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    def __init__(self,lang='te',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
                do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False):
        super(TeluguNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)

    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(TeluguNormalizer,self).normalize(text)

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0c64','\u0964')
        text=text.replace('\u0c65','\u0965')

        # dependent vowels
        text=text.replace('\u0c46\u0c56','\u0c48')

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0c00-\u0c7f]):','\\1\u0c03',text)

        return text

    def get_char_stats(self,text):
        pass 

class KannadaNormalizer(BaseNormalizer): 
    """
    Normalizer for the Kannada script. In addition to basic normalization by the super class, 

    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * canonicalize two-part dependent vowel signs
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    NUKTA='\u0CBC'

    def __init__(self,lang='kn',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',
            do_normalize_chandras=False,do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False):
        super(KannadaNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)


    def normalize(self,text): 

        # common normalization for Indic scripts 
        text=super(KannadaNormalizer,self).normalize(text)

        if self.remove_nuktas:
            text=text.replace(KannadaNormalizer.NUKTA,'')

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0ce4','\u0964')
        text=text.replace('\u0ce5','\u0965')

        # dependent vowels
        text=text.replace('\u0cbf\u0cd5','\u0cc0')
        text=text.replace('\u0cc6\u0cd5','\u0cc7')
        text=text.replace('\u0cc6\u0cd6','\u0cc8')
        text=text.replace('\u0cc6\u0cc2','\u0cca')
        text=text.replace('\u0cca\u0cd5','\u0ccb')

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0c80-\u0cff]):','\\1\u0c83',text)

        return text


class MalayalamNormalizer(BaseNormalizer): 
    """
    Normalizer for the Malayalam script. In addition to basic normalization by the super class, 

    * Replace the reserved character for poorna virama (if used) with the recommended generic Indic scripts poorna virama 
    * canonicalize two-part dependent vowel signs
    * Change from old encoding of chillus (till Unicode 5.0) to new encoding
    * replace colon ':' by visarga if the colon follows a charcter in this script 
    """

    CHILLU_CHAR_MAP= {
                    '\u0d7a': '\u0d23', 
                    '\u0d7b': '\u0d28',
                    '\u0d7c': '\u0d30',
                    '\u0d7d': '\u0d32',
                    '\u0d7e': '\u0d33',
                    '\u0d7f': '\u0d15',
                    # Unicode 9.0
                    '\u0d54': '\u0d2e',
                    '\u0d55': '\u0d2f',
                    '\u0d56': '\u0d34',
                 }

    def _canonicalize_chillus(self,text):
        # Note: This will cause confusion between chillu-based virama and half-u
        # Recommended to use final_virama_to_half_u_explicit() before this
        for chillu, char in MalayalamNormalizer.CHILLU_CHAR_MAP.items(): 
            text=text.replace(chillu,'{}\u0d4d'.format(char)) 
        return text
    
    def _intermediate_virama_to_chillus(self,text):
        # Convert intermediate virama-consonants to chillu forms
        # Does not convert final virama-consonants, since it's ambiguous (if it's half-u or glottal-stop)
        text=re.sub('\u0d23\u0d4d([\u0d00-\u0d7f])','\u0d7a\\1',text)
        text=re.sub('\u0d28\u0d4d([\u0d00-\u0d7f])','\u0d7b\\1',text)
        text=re.sub('\u0d30\u0d4d([\u0d00-\u0d7f])','\u0d7c\\1',text)
        text=re.sub('\u0d32\u0d4d([\u0d00-\u0d7f])','\u0d7d\\1',text)
        text=re.sub('\u0d33\u0d4d([\u0d00-\u0d7f])','\u0d7e\\1',text)
        text=re.sub('\u0d15\u0d4d([\u0d00-\u0d7f])','\u0d7f\\1',text)
        text=re.sub('\u0d2e\u0d4d([\u0d00-\u0d7f])','\u0d54\\1',text)
        text=re.sub('\u0d2f\u0d4d([\u0d00-\u0d7f])','\u0d55\\1',text)
        text=re.sub('\u0d34\u0d4d([\u0d00-\u0d7f])','\u0d56\\1',text)
        return text
    
    def _all_virama_to_chillus(self,text):
        # Warning: Use `_intermediate_virama_to_chillus()` unless you know what you're doing
        # Convert all virama-consonants to chillu forms
        text=text.replace('\u0d23\u0d4d','\u0d7a')
        text=text.replace('\u0d28\u0d4d','\u0d7b')
        text=text.replace('\u0d30\u0d4d','\u0d7c')
        text=text.replace('\u0d32\u0d4d','\u0d7d')
        text=text.replace('\u0d33\u0d4d','\u0d7e')
        text=text.replace('\u0d15\u0d4d','\u0d7f')
        text=text.replace('\u0d2e\u0d4d','\u0d54')
        text=text.replace('\u0d2f\u0d4d','\u0d55')
        text=text.replace('\u0d34\u0d4d','\u0d56')
        return text
    
    def _final_virama_to_half_u_explicit(self,text):
        # Chandrakala at the end of word is always half-u
        # Make it explicit: അവന്‌ -> അവനു് 
        return re.sub('([\u0d15-\u0d3a])\u0d4d([^\u0d00-\u0d7f]|$)', '\\1\u0d41\u0d4d\\2', text)
    
    def _final_virama_to_u(self,text):
        # By doing this, you'll always implicitly interpret final-u as half-u (as per pre-modern Grammar)

        # അവനു് --> അവനു (Assuming explicit-half-u might also have occured in middle positions)
        text = re.sub('([\u0d15-\u0d3a])\u0d41\u0d4d', '\\1\u0d41', text)
        # അവന്‌ -> അവനു (Only at final positions)
        return re.sub('([\u0d15-\u0d3a])\u0d4d([^\u0d00-\u0d7f]|$)', '\\1\u0d41\\2', text)

    def _correct_geminated_T(self,text):
        return text.replace('\u0d31\u0d4d\u0d31','\u0d1f\u0d4d\u0d1f')

    def __init__(self,lang='ml',remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
                do_explicit_half_u=False,do_canonicalize_chillus=False,do_half_u_to_u=False, do_correct_geminated_T=False,
                do_convert_viramas_to_chillus=False,do_convert_all_viramas_to_chillus=False):
        super(MalayalamNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        self.do_explicit_half_u=do_explicit_half_u
        self.do_canonicalize_chillus=do_canonicalize_chillus
        self.do_half_u_to_u=do_half_u_to_u
        self.do_correct_geminated_T=do_correct_geminated_T

        self.do_convert_viramas_to_chillus=do_convert_viramas_to_chillus
        self.do_convert_all_viramas_to_chillus=do_convert_all_viramas_to_chillus

    def normalize(self,text): 

        # Change from old encoding of chillus (till Unicode 5.0) to new encoding
        # text=text.replace('\u0d28\u0d4d\u0d31','\u0d7b\u0d4d\u0d31') # ന്റ -> ൻ്റ 
        text=text.replace('\u0d23\u0d4d\u200d','\u0d7a')
        text=text.replace('\u0d28\u0d4d\u200d','\u0d7b')
        text=text.replace('\u0d30\u0d4d\u200d','\u0d7c')
        text=text.replace('\u0d32\u0d4d\u200d','\u0d7d')
        text=text.replace('\u0d33\u0d4d\u200d','\u0d7e')
        text=text.replace('\u0d15\u0d4d\u200d','\u0d7f')
        # Unicode 9.0 introduces 3 new chillus
        text=text.replace('\u0d2e\u0d4d\u200d','\u0d54')
        text=text.replace('\u0d2f\u0d4d\u200d','\u0d55')
        text=text.replace('\u0d34\u0d4d\u200d','\u0d56')
        # Dot reph to chillu r
        text=text.replace('\u0d4e','\u0d7c')

        # common normalization for Indic scripts 
        text=super(MalayalamNormalizer,self).normalize(text)

        # Vertical/Circular Virama (Old Orthography) to Candrakkala
        text=text.replace('\u0d3b','\u0d4d')
        text=text.replace('\u0d3c','\u0d4d')

        if self.do_explicit_half_u:
            text=self._final_virama_to_half_u_explicit(text)
        
        if self.do_half_u_to_u:
            text=self._final_virama_to_u(text)

        # Normalize chillus
        if self.do_canonicalize_chillus:
            text=self._canonicalize_chillus(text)
        elif self.do_convert_viramas_to_chillus:
            text=self._intermediate_virama_to_chillus(text)
        elif self.do_convert_all_viramas_to_chillus:
            text=self._all_virama_to_chillus(text)

        # replace the poorna virama codes specific to script 
        # with generic Indic script codes
        text=text.replace('\u0d64','\u0964')
        text=text.replace('\u0d65','\u0965')

        # dependent vowels
        text=text.replace('\u0d46\u0d3e','\u0d4a')
        text=text.replace('\u0d47\u0d3e','\u0d4b')

        # au forms
        text=text.replace('\u0d46\u0d57','\u0d4c')
        text=text.replace('\u0d57','\u0d4c')
        
        # Old orthographic germination ഺ -> റ്റ
        text=text.replace('\u0d3a','\u0d31\u0d4d\u0d31')

        # correct geminated T
        if self.do_correct_geminated_T:
            text=self._correct_geminated_T(text)

        if self.do_colon_to_visarga: # correct visarga 
            text=re.sub(r'([\u0d00-\u0d7f]):','\\1\u0d03',text)

        return text

class SinhalaNormalizer(BaseNormalizer):

    MISRA_TO_SUDDA_CONSONANTS_MAP = {
        # mahA-prAna -> alpa-prAna
        '\u0D9B': '\u0D9A', # kh->k
        '\u0D9D': '\u0D9C', # gh->g
        '\u0DA1': '\u0DA0', # ch->c
        '\u0DA3': '\u0DA2', # jh->j
        '\u0DA8': '\u0DA7', # .th->.t
        '\u0DAA': '\u0DA9', # .dh->.d
        '\u0DAE': '\u0DAD', # th->t
        '\u0DB0': '\u0DAF', # dh->d
        '\u0DB5': '\u0DB4', # ph->p
        '\u0DB7': '\u0DB6', # bh->b

        # Sibilants
        '\u0DC1': '\u0DC3', # ;s -> s
        '\u0DC2': '\u0DC3', # .s -> s
        
        # Nasals
        # '\u0D9E': '\u0D9F',
        '\u0D9E': '\u0DAB', # ;n -> .n (Very approx)
        '\u0DA4': '\u0DAB', # ~n -> .n (Very approx)
        '\u0DB1': '\u0DAB', #  n -> .n

        # Misc
        '\u0DC6': '\u0DB4', # f->p
        # TODO: Handle ඥ and ඦ 
    }

    MISRA_TO_SUDDA_VOWELS_MAP = {
        # Independent
        '\u0D93': '\u0D85\u0DBA\u0DD2', # ඓ -> අයි (ai->ayi)
        '\u0D96': '\u0D85\u0DC0\u0DD4', # ඖ -> අවු (au->avu)
        '\u0D8D': '\u0DBB\u0DD4', # ඍ -> රු  (ṛ->ru)
        '\u0D8E': '\u0DBB\u0DD6', # ඎ -> රූ (ṝ->rū)
        '\u0D8F': '\u0DBD\u0DD2', # ඏ -> ලි (ḷ->li)
        '\u0D90': '\u0DBD\u0DD3', # ඐ -> ලී (ḹ->lī)

        # Dependent
        '\u0DDB': '\u0DBA\u0DD2', # ෛ -> යි 
        '\u0DDE': '\u0DC0\u0DD4', # ෞ -> වු 
        '\u0DD8': '\u0DCA\u0DBB\u0DD4', # ෘ ->  ්රු 
        '\u0DF2': '\u0DCA\u0DBB\u0DD6', # ෲ ->  ්රූ 
        '\u0DDF': '\u0DCA\u0DBD\u0DD2', # ෟ ->  ්ලි 
        '\u0DF3': '\u0DCA\u0DBD\u0DD3', # ෳ ->  ්ලී 
    }
    
    def __init__(self,lang,remove_nuktas=False,decompose_nuktas=False,nasals_mode='do_nothing',do_normalize_chandras=False,
                do_normalize_vowel_ending=False,do_normalize_numerals=False,convert_numerals_to_native=False,do_colon_to_visarga=False,
                misra_consonants_to_suddha=False,misra_vowels_to_suddha=False):
        super(SinhalaNormalizer,self).__init__(lang,remove_nuktas,decompose_nuktas,nasals_mode,do_normalize_chandras,do_normalize_vowel_ending,do_normalize_numerals,convert_numerals_to_native,do_colon_to_visarga)
        
        self.misra_consonants_to_suddha=misra_consonants_to_suddha
        self.misra_vowels_to_suddha=misra_vowels_to_suddha
        
        self.misra_consonants_to_suddha_converter = str.maketrans(SinhalaNormalizer.MISRA_TO_SUDDA_CONSONANTS_MAP)
        self.misra_vowels_to_suddha_converter = str.maketrans(SinhalaNormalizer.MISRA_TO_SUDDA_VOWELS_MAP)
    
    def normalize(self, text):
        # common normalization for Indic scripts 
        text=super(SinhalaNormalizer,self).normalize(text)

        ## Taken from: https://github.com/google/language-resources/blob/master/si/normalize_text.py
        # Vowel letters; cf. Table 13-2 in The Unicode Standard Version 9.0:
        text = text.replace('\u0D85\u0DCF', '\u0D86')  # අා -> ආ
        text = text.replace('\u0D85\u0DD0', '\u0D87')  # අැ -> ඇ
        text = text.replace('\u0D85\u0DD1', '\u0D88')  # අෑ -> ඈ
        text = text.replace('\u0D8B\u0DDF', '\u0D8C')  # උෟ -> ඌ
        text = text.replace('\u0D8D\u0DD8', '\u0D8E')  # ඍෘ -> ඎ
        text = text.replace('\u0D8F\u0DDF', '\u0D90')  # ඏෟ -> ඐ
        text = text.replace('\u0D91\u0DCA', '\u0D92')  # එ් -> ඒ
        text = text.replace('\u0D92\u0DCA', '\u0D92')  # ඒ් -> ඒ  (redundant virama)
        text = text.replace('\u0D91\u0DD9', '\u0D93')  # එෙ -> ඓ
        text = text.replace('\u0D94\u0DDF', '\u0D96')  # ඔෟ -> ඖ
        # Dependent vowel signs:
        text = text.replace('\u0DD9\u0DD9', '\u0DDB')  # කෙෙ -> කෛ
        text = text.replace('\u0DD8\u0DD8', '\u0DF2')  # කෘෘ -> කෲ

        # Misra superset to Suddha subset
        # Warning: Do not use for Pali
        if self.misra_consonants_to_suddha:
            text = text.translate(self.misra_consonants_to_suddha_converter)
        if self.misra_vowels_to_suddha:
            text = text.translate(self.misra_vowels_to_suddha_converter)

        if self.do_colon_to_visarga: # correct visarge 
            text=re.sub(r'([\u0d80-\u0dff]):','\\1\u0d83',text)
        return text

class UrduShahmukhiNormalizer(NormalizerI):
    '''Uses UrduHack library.
    https://docs.urduhack.com/en/stable/_modules/urduhack/normalization/character.html#normalize
    '''
    EAST_ARABIC_NUMERALS = "۰۱۲۳۴۵۶۷۸۹"

    def __init__(self, lang='ur', remove_diacritics=True, do_normalize_numerals=False,convert_numerals_to_native=False):
        self.lang = lang
        self.remove_diacritic_marks = remove_diacritics
        self.normalize_numerals = do_normalize_numerals
        self.convert_numerals_to_native = convert_numerals_to_native

        if lang == 'ks':
            # Diacritics are very important in Kashmiri, and always written & expected
            # Also, UrduHack doesnot drop Kashmiri-specific diacritics
            self.remove_diacritic_marks = False

        from importlib import import_module
        self.preprocessing = import_module('urduhack.preprocessing')
        self.normalization = import_module('urduhack.normalization.character')
        self.arabic_normalizer = str.maketrans({
            ',': '،',
            '?': '؟',
            '؛': ';',
            '٪': '%',

            '٫': '.', # Arabic decimal point
            '٬': ',', # Arabic thousands separator
            '؍': '/', # Arabic date separator
            'ࣇ': 'لؕ', # https://wikipedia.org/wiki/%E0%A3%87
            'ﷲ': 'اللہ',
        })
        
        self.numerals_normalizer = str.maketrans({
            native: str(i) for i, native in enumerate(UrduShahmukhiNormalizer.EAST_ARABIC_NUMERALS)
        })
        self.numerals_to_persian = str.maketrans({
            str(i): native for i, native in enumerate(UrduShahmukhiNormalizer.EAST_ARABIC_NUMERALS)
        })
    
    def normalize(self, text):
        text = self._normalize_punctuations(text)
        # text = self.preprocessing.normalize_whitespace(text)

        if self.remove_diacritic_marks:
            text = self.normalization.remove_diacritics(text)
        text = self.normalization.normalize_characters(text)
        text = text.translate(self.arabic_normalizer)
        if self.normalize_numerals:
            text = text.translate(self.numerals_normalizer)
        elif self.convert_numerals_to_native:
            text = text.translate(self.numerals_to_persian)
        text = self.normalization.normalize_combine_characters(text)

        text = self.normalization.punctuations_space(text)
        # text = self.preprocessing.digits_space(text)
        text = self.preprocessing.english_characters_space(text)
        return text

class SindhiNormalizer(UrduShahmukhiNormalizer):
    def __init__(self, lang='sd', remove_diacritics=True, do_normalize_numerals=False,convert_numerals_to_native=False):
        super().__init__(lang, remove_diacritics, do_normalize_numerals, convert_numerals_to_native)

        self.urdu_to_sindhi = str.maketrans({
            'ی': 'ي',
            'ے': 'ي',
            'ہ': 'ه', # Urdu gol-he to Arabic choti-he
            'ٹ': 'ٽ',
            'ڈ': 'ڊ',
            'ڑ': 'ڙ',
            'ݙ': 'ڏ', # Saraiki implosive to Sindhi
            # Below are ambiguous, uncomment for extreme cases
            # 'ٹھ': 'ٺ',
            # 'ڈھ': 'ڍ',
            # 'ڑھ': 'ڙه',
            # 'تھ': 'ٿ',
            # 'دھ': 'ڌ',
            # 'پھ': 'ڦ',
            # 'بھ': 'ڀ',
        })
    
    def normalize(self, text):
        text = super().normalize(text)
        text = re.sub(r"ھ\B", "ه", text) # Any intermediate do-chasmi can be converted to Arabic he
        text = re.sub('([^ڙجگ])ھ', r'\1ه', text) # Except final {گھ, جھ, ڙھ}, all other do-chasmi endings can be converted to Arabic he
        return text.translate(self.urdu_to_sindhi)


class ArabicNormalizer(NormalizerI):
    '''
    Uses PyArabic Library:
    https://github.com/linuxscout/pyarabic/blob/master/doc/features.md
    '''

    def __init__(self, lang='ar', remove_diacritics=True, do_normalize_numerals=False,convert_numerals_to_native=False):
        self.lang = lang
        self.remove_diacritic_marks = remove_diacritics
        self.normalize_numerals = do_normalize_numerals
        self.convert_numerals_to_native = convert_numerals_to_native

        from importlib import import_module
        self.normalizer = import_module('pyarabic.araby')
        self.araby_trans = import_module('pyarabic.trans')
    
    def normalize(self, text):
        text = self._normalize_punctuations(text)
        if self.remove_diacritic_marks:
            # text = self.normalizer.strip_harakat(text)
            # text = self.normalizer.strip_tashkeel(text)
            text = self.normalizer.strip_diacritics(text)
        text = self.normalizer.strip_tatweel(text)
        text = self.normalizer.normalize_ligature(text)
        if self.normalize_numerals:
            text = self.araby_trans.normalize_digits(text)
        elif self.convert_numerals_to_native:
            text = self.araby_trans.normalize_digits(text, source='all', out='east')
        return text

class PersianNormalizer(NormalizerI):
    def __init__(self, lang='fa', remove_diacritics=True, do_normalize_numerals=False,convert_numerals_to_native=False):
        self.lang = lang

        from hazm import Normalizer as HazmNormalizer
        self.normalizer = HazmNormalizer(persian_numbers=convert_numerals_to_native, remove_diacritics=remove_diacritics, persian_style=False)

        from parsivar import Normalizer as ParsivarNormalizer
        self.final_normalizer = ParsivarNormalizer()
    
    def normalize(self, text):
        text = self._normalize_punctuations(text)
        text = self.normalizer.normalize(text)
        return self.final_normalizer.normalize(text)

class NormalityEnglishNormalizer(NormalizerI):
    '''Uses Normality library.
    https://github.com/pudo/normality/blob/2fe711a0264e6ed4028b7f927eb641ffed014db0/normality/__init__.py#L35
    '''

    def __init__(self, lang, lowercase=False, ascii_only=True, **kwargs):
        self.lang = lang
        self.lowercase = lowercase
        self.ascii = ascii_only
        self.kwargs = kwargs

        import normality
        self._normalize = normality.normalize
    
    def normalize(self, text):
        return self._normalize(text, lowercase=self.lowercase, ascii=self.ascii, **self.kwargs)


class EnglishNormalizer(NormalizerI):
    '''Uses Clean-Text Library
    https://github.com/jfilter/clean-text/blob/90946c2cc8650929fe6487b70236b39348085fc8/cleantext/clean.py#L199
    '''

    def __init__(self, lang, lowercase=False, ascii_only=True, fix_unicode=False, strip_lines=False, **kwargs):
        self.lang = lang
        self.lowercase = lowercase
        self.ascii = ascii_only
        self.fix_unicode = fix_unicode
        self.strip_lines = strip_lines
        self.kwargs = kwargs

        import cleantext
        # Patch for performance
        from unidecode import unidecode_expect_ascii
        cleantext.unidecode = unidecode_expect_ascii

        self._normalize = cleantext.clean
    
    def capitalize(self, text):
        return re.sub('([0-9a-zA-Z])', lambda x: x.groups()[0].upper(), text, 1)
    
    def normalize(self, text):
        # Remove space between word and punctuation. https://stackoverflow.com/a/18878970
        text = re.sub(r'\s([?.!"](?:\s|$))', r'\1', text)
        # text = text.capitalize()
        text = self.capitalize(text)
        return self._normalize(text, lower=self.lowercase, to_ascii=self.ascii, fix_unicode=self.fix_unicode,
                     strip_lines=self.strip_lines, **self.kwargs)



class IndicNormalizerFactory(object):
    """
    Factory class to create language specific normalizers. 

    """

    def get_normalizer(self,language,**kwargs):
        """
            Call the get_normalizer function to get the language specific normalizer

            Paramters: 
            |language: language code
            |remove_nuktas: boolean, should the normalizer remove nukta characters 
        """
        normalizer=None
        if language in ['hi','mr','kK','ne','sd_IN']:
            normalizer=DevanagariNormalizer(lang=language, **kwargs)
        elif language in ['sa']:
            normalizer=SanskritNormalizer(lang=language, **kwargs)
        elif language in ['ks_IN']:
            normalizer=KashmiriDevanagariNormalizer(lang=language, **kwargs)
        elif language in ['ur','pnb','skr','ks']:
            normalizer = UrduShahmukhiNormalizer(lang=language, **kwargs)
        elif language in ['sd']:
            normalizer = SindhiNormalizer(lang=language, **kwargs)
        elif language in ['ar']:
            normalizer = ArabicNormalizer(lang=language, **kwargs)
        elif language in ['fa']:
            normalizer = PersianNormalizer(lang=language, **kwargs)
        elif language in ['pa']:
            normalizer=GurmukhiNormalizer(lang=language, **kwargs)
        elif language in ['gu']:
            normalizer=GujaratiNormalizer(lang=language, **kwargs)
        elif language in ['bn']:
            normalizer=BengaliNormalizer(lang=language, **kwargs)
        elif language in ['as']:
            normalizer=BengaliNormalizer(lang=language, **kwargs)
        elif language in ['or']:
            normalizer=OriyaNormalizer(lang=language, **kwargs)
        elif language in ['ml']:
            normalizer=MalayalamNormalizer(lang=language, **kwargs)
        elif language in ['kn']:
            normalizer=KannadaNormalizer(lang=language, **kwargs)
        elif language in ['ta']:
            normalizer=TamilNormalizer(lang=language, **kwargs)
        elif language in ['te']:
            normalizer=TeluguNormalizer(lang=language, **kwargs)
        elif language in ['si']:
            normalizer=SinhalaNormalizer(lang=language, **kwargs)
        elif language in ['en']:
            normalizer = EnglishNormalizer(lang=language, **kwargs)
        else:    
            normalizer=BaseNormalizer(lang=language, **kwargs)

        return normalizer    

    def is_language_supported(self,language): 
        """
        Is the language supported?
        """
        if language in ['hi','mr','sa','kK','ne','sd_IN','ks_IN',
                        'pa',
                        'gu',
                        'bn','as',
                        'or',
                        'ml',
                        'kn',
                        'ta',
                        'te',
                        'si',
                        'ur','pnb','sd','skr','ks',
                        'ar','fa',
                        'en']:
            return True
        else:
            return False


if __name__ == '__main__': 

    if len(sys.argv)<4:
        print("Usage: python normalize.py <infile> <outfile> <language> [<replace_nukta(True,False)>] [<normalize_nasals(do_nothing|to_anusvaara_strict|to_anusvaara_relaxed|to_nasal_consonants)>]") 
        sys.exit(1)

    language=sys.argv[3]
    remove_nuktas=False
    normalize_nasals='do_nothing'
    if len(sys.argv)>=5:
        remove_nuktas=bool(sys.argv[4])
    if len(sys.argv)>=6:
        normalize_nasals=sys.argv[5]

    # create normalizer
    factory=IndicNormalizerFactory()
    normalizer=factory.get_normalizer(language,remove_nuktas=remove_nuktas,nasals_mode=normalize_nasals)

    # DO normalization 
    with codecs.open(sys.argv[1],'r','utf-8') as ifile:
        with codecs.open(sys.argv[2],'w','utf-8') as ofile:
            for line in ifile.readlines():
                normalized_line=normalizer.normalize(line)
                ofile.write(normalized_line)
   
    ## gather status about normalization 
    #with codecs.open(sys.argv[1],'r','utf-8') as ifile:
    #    normalizer=DevanagariNormalizer()
    #    text=string.join(ifile.readlines(),sep='')
    #    normalizer.get_char_stats(text)
