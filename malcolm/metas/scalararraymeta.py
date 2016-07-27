from malcolm.metas.scalarmeta import ScalarMeta

class ScalarArrayMeta(ScalarMeta):
    # intermediate class so TableMeta can say "only arrays"
    pass
