"""Shared unrest state and mocked notification fixture."""
from support import Runner, Table, List, Component, Ware


class UnrestFixture:
    def setUp(self):
        self.run = Runner()
        self.sector = Component(exists=True, isplayerowned=True, knownname='Sector')
        self.hub = Component(exists=True, iswreck=False, sector=self.sector, owner='ownerless', knownname='Hub')
        self.r = Table(Level=5, Target=0, Hub=self.hub, Operational=True, PauseOffers=False,
                       Wares=Table(), Categories=Table(), GrowthSeconds=0.0, Last=0.0)
        self.run.env.update(R=self.r, faction=Table(player='player',ownerless='ownerless',ce_unrest='raiders'))
        self.run.library('md.CE_Unrest.Ensure')
        self.u = self.r.Unrest
        self.messages=[]
        self.run.stubs['md.CE_UnrestNotifications.Popup']=lambda:self.messages.append(('popup',self.run.env['IncidentText']))
        self.run.native['show_notification']=lambda n:self.messages.append(('ticker',self.run.expr(n.get('text'))))
        self.run.native['write_to_logbook']=lambda n:self.messages.append(('log',self.run.expr(n.get('text'))))

    def add(self, name, category=1, reserve=0, rate=3600):
        ware=Ware(name)
        self.r.Wares[ware]=Table(Active=True,Rate=rate,Reserve=reserve)
        self.r.Categories[ware]=category
        return ware

    def ready(self):
        self.u.update(Eligible=True,Grace=0.0)
        for ware in self.r.Wares:self.u.Wares[ware]=0.0

    def advance(self, seconds):
        self.run.env['player']['age']+=seconds
        self.run.library('md.CE_Reserves.Accrue')

    def score(self, score):
        self.u.Scores=List([float(score),0.0,0.0])
        self.run.library('md.CE_Unrest.Evaluate')

