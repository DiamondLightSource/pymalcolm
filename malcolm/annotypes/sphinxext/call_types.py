# Autodoc event handlers
def skip_member(app, what, name, obj, skip, options):
    # Override @add_call_types to always be documented
    if name != "_gorg" and (hasattr(obj, "call_types") or
                            hasattr(obj, "return_type")):
        return False


def process_docstring(app, what, name, obj, options, lines):
    # Work out if we need to work out the call types and return types
    needs_call_types = True
    needs_return_type = True
    for line in lines:
        strip = line.strip()
        if strip.startswith(":type"):
            needs_call_types = False
        elif strip.startswith(":rtype"):
            needs_return_type = False
    # If we have annotated with @add_call_types, or this is a WithCallTypes
    # instance, and we need call_types and return_type, make them
    if needs_call_types and hasattr(obj, "call_types"):
        for k, anno in obj.call_types.items():
            lines.append(":param %s: %s" % (k, anno.description))
            typ = getattr(anno.typ, "__name__", None)
            if typ:
                lines.append(":type %s: %s" % (k, typ))
            lines.append("")
    if needs_return_type and hasattr(obj, "return_type"):
        # If we have a return type and it isn't the object itself
        rt = obj.return_type
        if rt and rt.typ != obj:
            typ = getattr(rt.typ, "__name__", None)
            if typ:
                # Don't include the return description if no type given
                lines.append(":returns: %s" % rt.description)
                lines.append(":rtype: %s" % typ)


def setup(app):
    app.connect('autodoc-skip-member', skip_member)
    app.connect('autodoc-process-docstring', process_docstring)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
