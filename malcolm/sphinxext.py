from sphinx.ext.autodoc import ClassDocumenter, FunctionDocumenter



def get_method_model_docstring(model):
    # Add a new docstring
    docstring = ["params:"]
    for param, vmeta in model.takes.elements.items():
        docstring.append(
            "    - %s (%s):" % (param, vmeta.doc_type_string()))
        description = vmeta.description.strip()
        if not description[-1] in ".?!,":
            description += "."
        if param in model.takes.required:
            default = "Required"
        elif param in model.defaults:
            default = "Default=%r" % (model.defaults[param],)
        else:
            default = "Optional"
        docstring.append(
            "        %s %s" % (description, default))
    docstring.append("")
    return docstring


class ParamClassDocumenter(ClassDocumenter):
    def get_doc(self, encoding=None, ignore=1):
        docstrings = super(ParamClassDocumenter, self).get_doc(encoding, ignore)
        already_there = docstrings and docstrings[-1][0] == "params:"
        if hasattr(self.object, "MethodModel") and not already_there:
            docstring = get_method_model_docstring(self.object.MethodModel)
            docstrings.append(docstring)
        return docstrings


class ParamFunctionDocumenter(FunctionDocumenter):
    def get_doc(self, encoding=None, ignore=1):
        docstrings = super(ParamFunctionDocumenter, self).get_doc(
            encoding, ignore)
        already_there = docstrings and docstrings[-1][0] == "params:"
        if hasattr(self.object, "MethodModel") and not already_there:
            docstring = get_method_model_docstring(self.object.MethodModel)
            docstrings.append(docstring)
        return docstrings


def setup(app):
    app.add_autodocumenter(ParamClassDocumenter)
    app.add_autodocumenter(ParamFunctionDocumenter)

