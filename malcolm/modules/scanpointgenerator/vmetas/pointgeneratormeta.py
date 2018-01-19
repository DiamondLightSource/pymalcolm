from scanpointgenerator import CompoundGenerator

from malcolm.core import NTUnion, Serializable, VMeta, Widget


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
@VMeta.register_annotype_converter(CompoundGenerator)
class PointGeneratorMeta(VMeta):

    attribute_class = NTUnion

    def default_widget(self):
        return Widget.NONE

    def validate(self, value):
        if value is None:
            return CompoundGenerator([], [], [])
        elif isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, dict):
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)

    def doc_type_string(self):
        return "CompoundGenerator"
