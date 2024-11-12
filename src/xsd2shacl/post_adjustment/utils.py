
from rdflib import BNode

def clear_graph(g,old_subjects):
    bnodes = []
    for s,p,o in g:
        if s in old_subjects:
            g.remove((s,p,o))
            if isinstance(o,BNode):
                bnodes.append(o)
        elif o in old_subjects:
            g.remove((s,p,o))
        if (s in bnodes) or (o in bnodes):
            if isinstance(o,BNode):
                bnodes.append(o)
            if isinstance(s,BNode):
                bnodes.append(s)
    for s,p,o in g:
      if (s in bnodes) or (o in bnodes):
        g.remove((s,p,o))

    return g

def update_graph(g,old_subjects,new_s):
    bnodes = []
    for s,p,o in g:
        if s in old_subjects:
            g.add((new_s, p, o))
            if isinstance(o,BNode):
                bnodes.append(o)
        elif o in old_subjects:
            g.add((s, p, new_s))
        if (s in bnodes) or (o in bnodes):
            if isinstance(o,BNode):
                bnodes.append(o)
            if isinstance(s,BNode):
                bnodes.append(s)
    for s,p,o in g:
      if (s in bnodes) or (o in bnodes):
        g.add((new_s, p, o))

    return g







