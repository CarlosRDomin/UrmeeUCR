def get_offer_range(is_seller, valuation):
	if is_seller:
		return u'max="{}" min="{}" value="{}" step="0.5"'.format(valuation+10, valuation-5, valuation)
	else:
		return u'max="{}" min="{}" value="{}" step="0.5"'.format(valuation+5, valuation-10, valuation)


def get_condition_show_waiting_for_offer(role):
	return u'((negotiation_round+{:d})%2 == 0)'.format(role.starts_first)
