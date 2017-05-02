from malcolm.core import Method, Attribute
from malcolm.gui.baseitem import BaseItem
from malcolm.gui.methoditem import MethodItem
from malcolm.gui.attributeitem import AttributeItem


class BlockItem(BaseItem):

    def _get_group_name(self, attr):
        meta = getattr(attr, "meta", None)
        if meta:
            tags = getattr(meta, "tags", [])
        else:
            tags = []
        groups = [x for x in tags if x.startswith("group:")]
        if groups:
            group_name = groups[0][len("group:"):]
            return group_name

    def ref_children(self):
        """Number of child objects our ref has"""
        nchildren = 0
        for name in self.ref:
            child = self.ref[name]
            # check for group, otherwise put it in place
            if self._get_group_name(child) is None:
                nchildren += 1
        return nchildren

    def create_children(self):
        for name in self.ref:
            child = self.ref[name]
            if isinstance(child, Attribute):
                attr = child
                item = AttributeItem(self.endpoint + (name,), attr)
                group_name = self._get_group_name(attr)
                if group_name is None:
                    parent_item = self
                else:
                    parent_endpoint = self.endpoint + (group_name,)
                    parent_item = self.items[parent_endpoint]
                parent_item.add_child(item)
                item.create_children()
            elif isinstance(child, Method):
                method = child
                item = MethodItem(self.endpoint + (name,), method)
                self.add_child(item)
                item.create_children()
