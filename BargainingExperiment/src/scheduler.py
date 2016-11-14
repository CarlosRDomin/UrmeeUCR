from collections import deque


def schedule_even_avoid_same_class_matching(l, n_rounds=None):
	"""
	Similar to round_robin_even, but only the first half of the list rotates, so that if you have a list containing
	two classes of users (eg: sellers and buyers), users of the same type won't be matched (eg: seller-seller).
	:param l: List containing users to get matched (each half of the list is assumed to belong to the same user class).
	:param n_rounds: Determines how many rounds of matches the generator should yield. Defaults to len(l)/2 if None.
	:return: Generator that returns n_rounds sets of matches from the items in the list l.
	"""
	n = len(l)
	n_rounds = n/2 if n_rounds is None else n_rounds
	fixed = l[0:n/2]
	rotating = deque(l[n/2:])

	# while True:
	for i in range(n_rounds):
		yield [[fixed[j], rotating[j]] for j in range(n/2)]
		rotating.rotate()

def round_robin_even(d, n):  # From http://stackoverflow.com/questions/14169122/generating-all-unique-pair-permutations
	for i in range(n - 1):
		yield [[d[j], d[-j-1]] for j in range(n/2)]
		d[0], d[-1] = d[-1], d[0]
		d.rotate()

def round_robin_odd(d, n):  # From http://stackoverflow.com/questions/14169122/generating-all-unique-pair-permutations
	for i in range(n):
		yield [[d[j], d[-j-1]] for j in range(n/2)]
		d.rotate()

def round_robin(n):  # From http://stackoverflow.com/questions/14169122/generating-all-unique-pair-permutations
	d = deque(range(1, n+1))
	if n % 2 == 0:
		return list(schedule_even_avoid_same_class_matching(list(d)))
	else:
		return list(round_robin_odd(d, n))


if __name__ == "__main__":
	all_perms = round_robin(8)
	for x in all_perms:
		print x