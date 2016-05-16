
def get_offer_range(is_seller, valuation):
    if is_seller:
        return u'max="{}" min="{}" value="{}" step="0.5"'.format(valuation+10, valuation-5, valuation)
    else:
        return u'max="{}" min="{}" value="{}" step="0.5"'.format(valuation+5, valuation-10, valuation)
