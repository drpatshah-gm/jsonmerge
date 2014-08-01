# vim:ts=4 sw=4 expandtab softtabstop=4
import re

class Strategy: pass

class Overwrite(Strategy):
    def merge(self, merger, base, head, schema, meta, **kwargs):
        return head

    def get_schema(self, merger, schema, meta, **kwargs):
        return merger.resolve_refs(schema)

class Version(Strategy):
    def merge(self, merger, base, head, schema, meta, limit=None, unique=True, **kwargs):
        if base is None:
            base = []
        else:
            base = list(base)

        if not unique or not base or base[0]['value'] != head:
            base.append(merger.add_meta(head, meta))
            if limit is not None:
                base = base[-limit:]

        return base

    def get_schema(self, merger, schema, meta, limit=None, **kwargs):

        if meta is not None:
            item = dict(meta)
        else:
            item = {}

        if 'properties' not in item:
            item['properties'] = {}

        item['properties']['value'] = merger.resolve_refs(schema)

        rv = { "items": item }

        if limit is not None:
            rv['maxItems'] = limit

        return rv

class Append(Strategy):
    def merge(self, merger, base, head, schema, meta, **kwargs):
        if not merger.is_type(head, "array"):
            raise TypeError("Head for an 'append' merge strategy is not an array")

        if base is None:
            base = []
        else:
            if not merger.is_type(base, "array"):
                raise TypeError("Base for an 'append' merge strategy is not an array")

            base = list(base)

        base += head
        return base

    def get_schema(self, merger, schema, meta, **kwargs):
        return merger.resolve_refs(schema)

class ObjectMerge(Strategy):
    def merge(self, merger, base, head, schema, meta, **kwargs):
        if not merger.is_type(head, "object"):
            raise TypeError("Head for an 'object' merge strategy is not an object")

        if base is None:
            base = {}
        else:
            if not merger.is_type(base, "object"):
                raise TypeError("Base for an 'object' merge strategy is not an object")

            base = dict(base)

        for k, v in head.items():

            subschema = None

            # get subschema for this element
            if schema is not None:
                p = schema.get('properties')
                if p is not None:
                    subschema = p.get(k)

                if subschema is None:
                    p = schema.get('patternProperties')
                    if p is not None:
                        for pattern, s in p.items():
                            if re.search(pattern, k):
                                subschema = s

                if subschema is None:
                    p = schema.get('additionalProperties')
                    if p is not None:
                        subschema = p.get(k)

            base[k] = merger.descend(subschema, base.get(k), v, meta)

        return base

    def get_schema(self, merger, schema, meta, **kwargs):

        for forbidden in ("oneOf", "allOf", "anyOf"):
            if forbidden in schema:
                raise TypeError("Type ambiguous schema")

        schema2 = dict(schema)

        def descend_keyword(keyword):
            p = schema.get(keyword)
            if p is not None:
                for k, v in p.items():
                    schema2[keyword][k] = merger.descend(v, meta)

        descend_keyword("properties")
        descend_keyword("patternProperties")
        descend_keyword("additionalProperties")

        return schema2
