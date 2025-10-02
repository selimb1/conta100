
def validate_cuit(cuit: str) -> bool:
    digits = [int(d) for d in cuit if d.isdigit()]
    if len(digits) != 11:
        return False
    coeffs = [5,4,3,2,7,6,5,4,3,2]
    s = sum(a*b for a,b in zip(coeffs, digits[:10]))
    mod = 11 - (s % 11)
    dv = 0 if mod == 11 else (9 if mod == 10 else mod)
    return dv == digits[-1]
