"""Conservative lexical retrieval. Chinese bigrams work without a tokenizer service."""
import re
from collections import Counter

STOP = {'the','a','an','is','are','of','to','how','what','do','does','i','my','in','on','for','and','can','when','should','it','we','with','为什么','如何','怎么','什么','哪些','多少','几个','几次','时候','我的','我们','可以','是否','一下'}


def tokens(text):
    terms = []
    for part in re.findall(r'[\u3400-\u9fff]+|[a-z0-9]+', text.lower()):
        if part.isascii():
            if len(part) > 1 and part not in STOP:
                terms.append(part)
        else:
            for stop in sorted(STOP, key=len, reverse=True):
                if not stop.isascii():
                    part = part.replace(stop, ' ')
            for run in part.split():
                terms.extend(run[i:i+2] for i in range(len(run)-1))
    return set(terms)


def chunks(text, size=900):
    # A hard excerpt boundary keeps provider prompts bounded and inspectable.
    return [text[i:i+size] for i in range(0, len(text), size)]


def retrieve(question, sources):
    query = tokens(question)
    if not query:
        return []
    frequencies = Counter(term for source in sources for term in tokens(source['text'] + ' ' + source['title']))
    hits = []
    for source in sources:
        best = None
        for excerpt in chunks(source['text']):
            shared = query & tokens(source['title'] + ' ' + excerpt)
            coverage = len(shared) / len(query)
            # Require a meaningful part of the query, not incidental shared characters.
            if not shared or coverage < .22 or (len(query) >= 5 and len(shared) < 2):
                continue
            score = sum(1 / frequencies[t] for t in shared) + coverage
            candidate = {'id': source['id'], 'title': source['title'], 'excerpt': excerpt, 'score': round(score, 4)}
            if best is None or score > best['score']:
                best = candidate
        if best:
            hits.append(best)
    return sorted(hits, key=lambda h: (-h['score'], h['id']))[:4]
