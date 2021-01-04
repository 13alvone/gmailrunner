# Simple Summarizer
# Copyright (C) 2010-2012 Tristan Havelick
# Author: Tristan Havelick <tristan@havelick.com>
# URL: <https://github.com/thavelick/summarize/>
# For license information, see https://github.com/thavelick/summarize/blob/master/LICENSE.TXT

"""
A summarizer based on the algorithm found in Classifier4J by Nick Lothan.
In order to summarize a document this algorithm first determines the
frequencies of the words in the document.  It then splits the document
into a series of sentences.  Then it creates a summary by including the
first sentence that includes each of the most frequent words.  Finally
summary's sentences are reordered to reflect that of those in the original
document.
"""

##//////////////////////////////////////////////////////
##  Simple Summarizer
##//////////////////////////////////////////////////////

from nltk.probability import FreqDist
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
import nltk.data


class SimpleSummarizer:

    # def reorder_sentences(self, output_sentences, input):
    #     output_sentences.sort(key=lambda s1, s2: input.find(s1) - input.find(s2))
    #     return output_sentences

    def get_summarized(self, input, num_sentences):
        tokenizer = RegexpTokenizer('\w+')

        # get the frequency of each word in the input
        base_words = [word.lower() for word in tokenizer.tokenize(input)]
        words = [word for word in base_words if word not in stopwords.words()]
        word_frequencies = FreqDist(words)

        # create a set of the most frequent words
        x = word_frequencies.items()
        most_frequent_words = [pair[0] for pair in word_frequencies.items()][:100]

        # break the input up into sentences.  working_sentences is used
        # for the analysis, but actual_sentences is used in the results
        # so capitalization will be correct.

        sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
        actual_sentences = sent_detector.tokenize(input)
        working_sentences = [sentence.lower() for sentence in actual_sentences]

        # iterate over the most frequent words, and add the first sentence
        # that includes each word to the result.
        output_sentences = []

        for word in most_frequent_words:
            for i in range(0, len(working_sentences)):
                if (word in working_sentences[i]
                        and actual_sentences[i] not in output_sentences):
                    output_sentences.append(actual_sentences[i])
                    break
                if len(output_sentences) >= num_sentences: break
            if len(output_sentences) >= num_sentences: break
        return output_sentences

    def summarize(self, input, num_sentences):
        return " ".join(self.get_summarized(input, num_sentences))
