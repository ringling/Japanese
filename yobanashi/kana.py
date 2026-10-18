"""Kana → romaji (same table as the shukudai skill, so Anki entries match)."""
ROMA = {'きゃ':'kya','きゅ':'kyu','きょ':'kyo','しゃ':'sha','しゅ':'shu','しょ':'sho','ちゃ':'cha','ちゅ':'chu','ちょ':'cho',
'にゃ':'nya','にゅ':'nyu','にょ':'nyo','ひゃ':'hya','ひゅ':'hyu','ひょ':'hyo','みゃ':'mya','みゅ':'myu','みょ':'myo',
'りゃ':'rya','りゅ':'ryu','りょ':'ryo','ぎゃ':'gya','ぎゅ':'gyu','ぎょ':'gyo','じゃ':'ja','じゅ':'ju','じょ':'jo',
'びゃ':'bya','びゅ':'byu','びょ':'byo','ぴゃ':'pya','ぴゅ':'pyu','ぴょ':'pyo','てぃ':'ti','でぃ':'di','ふぁ':'fa','ふぃ':'fi','ふぇ':'fe','ふぉ':'fo','うぃ':'wi','うぇ':'we','しぇ':'she','ちぇ':'che','じぇ':'je',
'あ':'a','い':'i','う':'u','え':'e','お':'o','か':'ka','き':'ki','く':'ku','け':'ke','こ':'ko','さ':'sa','し':'shi','す':'su','せ':'se','そ':'so',
'た':'ta','ち':'chi','つ':'tsu','て':'te','と':'to','な':'na','に':'ni','ぬ':'nu','ね':'ne','の':'no','は':'ha','ひ':'hi','ふ':'fu','へ':'he','ほ':'ho',
'ま':'ma','み':'mi','む':'mu','め':'me','も':'mo','や':'ya','ゆ':'yu','よ':'yo','ら':'ra','り':'ri','る':'ru','れ':'re','ろ':'ro','わ':'wa','を':'o','ん':'n',
'が':'ga','ぎ':'gi','ぐ':'gu','げ':'ge','ご':'go','ざ':'za','じ':'ji','ず':'zu','ぜ':'ze','ぞ':'zo','だ':'da','ぢ':'ji','づ':'zu','で':'de','ど':'do',
'ば':'ba','び':'bi','ぶ':'bu','べ':'be','ぼ':'bo','ぱ':'pa','ぴ':'pi','ぷ':'pu','ぺ':'pe','ぽ':'po','ぁ':'a','ぃ':'i','ぅ':'u','ぇ':'e','ぉ':'o'}


def kata2hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def romaji(kana):
    s, out, i = kata2hira(kana), '', 0
    while i < len(s):
        c = s[i]
        if c == 'っ' and i + 1 < len(s):
            nxt = ROMA.get(s[i+1:i+3]) or ROMA.get(s[i+1], '')
            out += nxt[:1]; i += 1; continue
        if c == 'ー':
            out += out[-1:] if out else ''; i += 1; continue
        two = s[i:i+2]
        if two in ROMA:
            out += ROMA[two]; i += 2; continue
        out += ROMA.get(c, c); i += 1
    return out


