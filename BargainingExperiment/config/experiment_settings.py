from BargainingExperiment.src.models import *  # (Do not modify this line!)

"""
NUMBER_OF_USERS indicates the number of users/players that will participate in the current experiment session.
It's a number, eg: 32 users.
"""
NUMBER_OF_USERS = 2

"""
SESSION_ORDER indicates how the matchings will be generated (play against the computer first, or play against other users first, how many rounds against the computer, etc.).
It's a list surrounded by square braquets "[]", and each item of the list is surrounded by parenthesis "()".
Inside the parenthesis, go two things, separated by a comma ",":
 (1) Who they'll be matched against: either the word "COMPUTER" or the word "USERS" (in CAPS LETTERS)
 (2) How many matches they'll play: a number (eg: 10, meaning 10 matches).
     Note that you can also use previous variables, like NUMBER_OF_USERS (so NUMBER_OF_USERS/2 would match each seller with every buyer once, for the USERS round)
Example list: SESSION_ORDER = [(COMPUTER, 5), (USERS, NUMBER_OF_USERS/2)]
Example effect: First, each user plays against the computer 5 times; then, each user plays every user of the other type (buyers vs sellers) once.
"""
SESSION_ORDER = [(COMPUTER, 3), (USERS, NUMBER_OF_USERS/2)]

"""
VALUATION_SET indicates the possible values that users (and the computer) can get their item valuated at.
It's a list of 4 numbers (may have decimals if desired): [seller_low, buyer_low, seller_high, buyer_high] (in that order).
As discussed, users are only allowed to choose from 2 values to make an offer: buyer_low and seller_high (the two central elements of the list).
Also, based on your notes, they should follow seller_low < buyer_low < seller_high < buyer_high.
"""
VALUATION_SET = [50, 60, 70, 100]

"""
PROB_SELLER_LOW and PROB_SELLER_HIGH represent the probabilities of assigning a valuation of seller_low or seller_high, respectively.
It's a decimal number representing a percentage, eg: 0.4 means 40%, so it needs to be between 0 and 1. PROB_SELLER_HIGH is automatically computed from PROB_SELLER_LOW.
"""
PROB_SELLER_LOW = 0.5
PROB_SELLER_HIGH = 1 - PROB_SELLER_LOW

"""
PROB_BUYER_LOW and PROB_BUYER_HIGH represent the probabilities of assigning a valuation of buyer_low or buyer_high, respectively.
It's a decimal number representing a percentage, eg: 0.4 means 40%, so it needs to be between 0 and 1. PROB_BUYER_LOW is automatically computed from PROB_BUYER_HIGH.
"""
PROB_BUYER_HIGH = 0.5
PROB_BUYER_LOW = 1 - PROB_BUYER_HIGH

"""
MATCH_STARTED_BY indicates who will make the first offer of a match (the seller, the buyer, or random).
It can take one of these 3 values: "SELLER_FIRST", "BUYER_FIRST", or "RANDOM_FIRST" (no quotes, and CAPS LETTERS).
For example, MATCH_STARTED_BY = SELLER_FIRST means that, in every match, the seller will always go first making an offer.
"""
MATCH_STARTED_BY = SELLER_FIRST

"""
MAX_ROUNDS indicates the maximum number of rounds two users (or a user and a computer) can play without reaching an agreement until the match is terminated.
It's a number, eg: 10 rounds.
"""
MAX_ROUNDS = 10

"""
INTEREST_PER_ROUND indicates how much of their potential earnings users lose after each round without agreeing on a price.
It's a decimal number representing a percentage, eg: 0.05 means 5%, 0.12 means 12% and so on, so it needs to be between 0 and 1.
"""
INTEREST_PER_ROUND = 0.05