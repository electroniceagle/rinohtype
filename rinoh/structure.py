# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from itertools import count, repeat

from .flowable import GroupedFlowables, StaticGroupedFlowables, LabeledFlowable
from .flowable import GroupedFlowablesStyle
from .number import format_number, NUMBER
from .paragraph import ParagraphStyle, ParagraphBase, Paragraph, ParagraphState
from .reference import Reference, Referenceable, REFERENCE, TITLE, PAGE
from .reference import Variable, PAGE_NUMBER, NUMBER_OF_PAGES
from .reference import SECTION_NUMBER, SECTION_TITLE
from .text import SingleStyledText, MixedStyledText, FixedWidthSpace, Tab
from .dimension import PT
from .style import PARENT_STYLE


__all__ = ['HeadingStyle', 'Heading', 'ListStyle', 'List', 'ListItem',
           'DefinitionListStyle', 'DefinitionList',
           'HeaderStyle', 'Header', 'FooterStyle', 'Footer',
           'TableOfContentsStyle', 'TableOfContents', 'TableOfContentsEntry']


class HeadingStyle(ParagraphStyle):
    attributes = {'numbering_style': NUMBER,
                  'numbering_separator': '.'}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


# TODO: share superclass with List (numbering)
class Heading(Referenceable, ParagraphBase):
    style_class = HeadingStyle

    def __init__(self, title, style=None, level=1, id=None):
        ParagraphBase.__init__(self, style)
        Referenceable.__init__(self, id)
        self.title = title
        self.level = level

    def __repr__(self):
        return '{}({}) (style={})'.format(self.__class__.__name__, self.title,
                                        self.style)

    def prepare(self, document):
        super().prepare(document)
        element_id = self.get_id(document)
        heading_counters = document.counters.setdefault(__class__, {})
        level_counter = heading_counters.setdefault(self.level, [])
        level_counter.append(self)

        number = 0
        for element in document.counters[__class__][self.level]:
            if element.get_style('numbering_style', document) is not None:
                number += 1
            if element is self:
                break
        numbering_style = self.get_style('numbering_style', document)
        if numbering_style is not None:
            formatted_number = format_number(number, numbering_style)
        else:
            formatted_number = ''
        document.set_reference(element_id, REFERENCE, formatted_number)
        document.set_reference(element_id, TITLE, self.title)

    def initial_state(self, document):
        numbering_style = self.get_style('numbering_style', document)
        if numbering_style is not None:
            formatted_number = Reference(self.get_id(document), REFERENCE)
            separator = self.get_style('numbering_separator', document)
            number = formatted_number + separator + FixedWidthSpace()
        else:
            number = ''
        text = MixedStyledText(number + self.title, parent=self)
        return ParagraphState(text.spans())

    def render(self, container, last_descender, state=None):
        if self.level == 1:
            container.page.section = self
        self.update_page_reference(container.page)
        return super().render(container, last_descender, state=state)


class ListStyle(GroupedFlowablesStyle):
    attributes = {'ordered': False,
                  'bullet': SingleStyledText('\N{BULLET}'),
                  'numbering_style': NUMBER,
                  'numbering_separator': ')'}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class List(GroupedFlowables):
    style_class = ListStyle

    def __init__(self, items, style=None):
        super().__init__(style)
        self.items = items

    def flowables(self, document):
        if self.get_style('ordered', document):
            separator = self.get_style('numbering_separator', document)
            numbering_style = self.get_style('numbering_style', document)
            numbers = (format_number(i, numbering_style) for i in count(1))
        else:
            separator = ''
            numbers = repeat(self.get_style('bullet', document))
        for number, item in zip(numbers, self.items):
            yield ListItem(number, separator, item, parent=self)


class ListItemNumber(Paragraph):
    def render(self, container, descender, state=None):
        before = container.cursor
        result = super().render(container, descender, state=state)
        container.advance(before - container.cursor)
        return result


class ListItem(LabeledFlowable):
    def __init__(self, number, separator, flowables, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.number = number
        self.label = ListItemNumber(self.number + separator, parent=self)
        self.flowables = StaticGroupedFlowables(flowables, parent=self)

    def label_flowable(self, document):
        return self.label

    def content_flowable(self, document):
        return self.flowables



class DefinitionListStyle(GroupedFlowablesStyle, ParagraphStyle):
    attributes = {'term_style': PARENT_STYLE,
                  'indentation': 10*PT}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class DefinitionList(GroupedFlowables):
    style_class = DefinitionListStyle

    def __init__(self, items, style=None):
        super().__init__(style)
        self.items = items
        for term, definition in items:
            term.parent = definition.parent = self

    def flowables(self, document):
        term_style = ParagraphStyle(space_above=0*PT,
                                    space_below=0*PT,
                                    base=PARENT_STYLE)
        for i, item in enumerate(self.items):
            term, definition = item
            term_par = Paragraph(term, style=term_style, parent=self)
            yield term_par
            yield definition


class HeaderStyle(ParagraphStyle):
    attributes = {}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class Header(ParagraphBase):
    style_class = HeaderStyle

    def spans(self):
        text = Variable(SECTION_NUMBER) + ' ' + Variable(SECTION_TITLE)
        return MixedStyledText(text, parent=self).spans()


class FooterStyle(ParagraphStyle):
    attributes = {}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class Footer(ParagraphBase):
    style_class = FooterStyle

    def spans(self):
        text = Variable(PAGE_NUMBER) + ' / ' + Variable(NUMBER_OF_PAGES)
        return MixedStyledText(text, parent=self).spans()


class TableOfContentsStyle(GroupedFlowablesStyle, ParagraphStyle):
    attributes = {'depth': 3}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class TableOfContents(GroupedFlowables):
    style_class = TableOfContentsStyle
    location = 'table of contents'

    def __init__(self, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.source = self

    def flowables(self, document):
        depth = self.get_style('depth', document)
        for flowable in (flowable for target in document.flowable_targets
                         for flowable in target.flowables):
            if isinstance(flowable, Heading) and flowable.level <= depth:
                flowable_id = flowable.get_id(document)
                text = [Reference(flowable_id, type=REFERENCE), Tab(),
                        Reference(flowable_id, type=TITLE), Tab(),
                        Reference(flowable_id, type=PAGE)]
                for reference in text:
                    reference.source = self
                entry = TableOfContentsEntry(text, level=flowable.level,
                                             parent=self)
                yield entry


class TableOfContentsEntry(Paragraph):
    def __init__(self, text_or_items, level, style=None, parent=None):
        super().__init__(text_or_items, style=style, parent=parent)
        self.level = level
