"""Narrow regression models for contracts observed in the last native load."""
import unittest
from lxml import etree as E
from support import Runner, Table, List
from test_construction import sequence, module


class Money(float):
    """Retain money through division, matching the logged normalization expression.

    This is deliberately a narrow fixture, not a model of every MD arithmetic rule.
    """
    def __truediv__(self, other): return Money(float(self) / float(other))
    def __rtruediv__(self, other): return Money(float(other) / float(self))
    def __add__(self, other):
        if type(other) is float:
            raise ValueError('Implicit floating point to money conversion')
        return Money(float(self) + float(other))


class NativeStartupContracts(unittest.TestCase):
    def test_combined_optional_and_existence_syntax_is_rejected(self):
        r = Runner()
        for expression in ["not @$ProfileWares.{'$' + $ProfileWare.id}?", "@$R.$Field?"]:
            with self.assertRaisesRegex(ValueError, 'cannot be combined'):
                r.expr(expression)
        r.env['R'] = Table(Field=1)
        self.assertTrue(r.expr('$R.$Field?'))
        self.assertEqual(r.expr('@$R.$Field'), 1)

    def test_sequence_properties_are_values_but_entries_cannot_be_stored(self):
        r = Runner(); macro = module('storage')
        r.env.update(Sequence=sequence([macro]), i=1)
        with self.assertRaisesRegex(ValueError, 'pseudo-values'):
            r.actions(E.fromstring('<actions><set_value name="$Entry" exact="$Sequence.{$i}"/></actions>'))
        r.actions(E.fromstring('<actions><set_value name="$Macro" exact="$Sequence.{$i}.macro"/><set_value name="$ID" exact="$Sequence.{$i}.id"/></actions>'))
        self.assertIs(r.env['Macro'], macro)
        self.assertEqual(r.env['ID'], '0')

    def test_original_budget_expression_exposes_money_conversion(self):
        r = Runner(); r.env.update(ProfileBudget=150000.0, ProfileAveragePrice=Money(4200))
        with self.assertRaisesRegex(ValueError, 'money conversion'):
            r.expr('$ProfileBudget / ($ProfileAveragePrice / 1Cr) / 10.0f + 0.5f')

    def test_budget_normalization_uses_numeric_credits_and_rounds_half_up(self):
        for budget, cents, expected in [(150000., 4200, 3570), (125.,100,130), (124.9,100,120), (1.,10000,10)]:
            with self.subTest(budget=budget, cents=cents):
                r = Runner()
                r.env.update(ProfileAddID='food', ProfileWares=Table({'$food':Table(averageprice=Money(cents),group=Table(id='food'))}),
                             ProfileDefinition=["food",1,budget,'budget'])
                r.env['ProfileDefinition'] = List(r.env['ProfileDefinition'])
                r.library('md.CE_PopulationProfiles.NormalizeBudget')
                self.assertEqual(r.env['ProfileDefinition'][3], expected)
                self.assertNotIsInstance(r.env['ProfileDefinition'][3], Money)


    def test_condition_only_cues_require_polling_or_onfail(self):
        # The native parser enforces this mode distinction; the XSD cannot.
        def validate(tree):
            for cue in tree.xpath('//cue[conditions/*]'):
                has_event=any(isinstance(n.tag,str) and n.tag.startswith('event_')
                              for n in cue.find('conditions').iter())
                if not has_event and cue.get('checkinterval') is None and cue.get('onfail') is None:
                    raise ValueError('event condition required: '+cue.get('name'))
        old=E.fromstring('<mdscript><cue name="State" namespace="this"><conditions><check_value value="false"/></conditions></cue></mdscript>')
        with self.assertRaisesRegex(ValueError,'event condition required: State'):
            validate(old)
        for tree in Runner().scripts.values():
            validate(tree)


if __name__ == '__main__': unittest.main()
