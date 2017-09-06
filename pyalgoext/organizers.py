import math
from pyalgotrade import dataseries


class OrganizerWindow(object):
    def __init__(self, windowSize, dtype=float, skipNone=True):
        assert(windowSize > 0)
        assert(isinstance(windowSize, int))
        self.__values = []
        self.__windowSize = windowSize
        self.__skipNone = skipNone

    def onNewValue(self, dateTime, value):
        if value is not None or not self.__skipNone:
            self.__values.append(value)
            if len(self.__values) > self.__windowSize:
                self.__values.pop(0)

    def getValues(self):
        return self.__values

    def getWindowSize(self):
        return self.__windowSize

    def windowFull(self):
        return len(self.__values) == self.__windowSize

    def getValue(self):
        raise NotImplementedError()


class EventBasedOrganizer(dataseries.SequenceDataSeries):
    def __init__(self, dataFeed, eventWindow, maxLen=dataseries.DEFAULT_MAX_LEN):
        dataseries.SequenceDataSeries.__init__(self, maxLen)
        self.__feed = dataFeed
        self.__feed.getNewValuesEvent().subscribe(self.__onNewValue)
        self.__eventWindow = eventWindow

    def __onNewValue(self, dateTime, bars):
        # Let the event window perform calculations.
        self.__eventWindow.onNewValue(dateTime, bars)
        # Get the resulting value
        newValue = self.__eventWindow.getValue()
        # Add the new value.
        self.appendWithDateTime(dateTime, newValue)

    def getFeed(self):
        return self.__feed

    def getEventWindow(self):
        return self.__eventWindow


class OrderRule(object):
    def __init__(self, concept, asc=False, weight=1):
        self.__concept = concept
        self.__asc = asc
        self.__weight = weight

    def getConcept(self):
        return self.__concept

    def isAsc(self):
        return self.__asc

    def getWeight(self):
        return self.__weight


class BasicOrganizerWindow(object):
    def __init__(self, feed, rules, groups=None):
        self.__feed = feed
        self.__rules = rules
        self.__groups = groups
        self.__value = None

    def onNewValue(self, dateTime, bars):
        members = self.__feed.getMembers()

        ranking = {}
        for instrument in members:
            ranking[instrument] = 0
        scores = {}

        ratio = 1
        if self.__groups:
            ratio = len(ranking) / float(self.__groups)

        for rule in self.__rules:
            concept = rule.getConcept()
            flip = rule.isAsc()
            weight = rule.getWeight()

            score = {}
            for instrument in members:
                if instrument in bars:
                    bar = bars[instrument]
                    score[instrument] = bar.getField(concept)
                else:
                    score[instrument] = None
            score = sorted(score.items(), key=(lambda item: ((item[1] is None) is flip, item[1])), reverse=flip)
            scores[concept] = score

            lastValue = None
            rankNum = 1
            prevRank = 1
            for instrument, value in score:
                rank = rankNum
                if value == lastValue:
                    rank = prevRank
                if value is not None:
                    ranking[instrument] += math.ceil(rank / ratio) * weight
                prevRank = rank
                lastValue = value
                rankNum += 1

        ranking = sorted(ranking.items(), key=(lambda item: item[1]), reverse=True)
        self.__value = ranking

    def getValue(self):
        return self.__value


class BasicOrganizer(EventBasedOrganizer):
    def __init__(self, feed, eventWindow, maxLen=dataseries.DEFAULT_MAX_LEN):
        super(BasicOrganizer, self).__init__(feed, eventWindow, maxLen)


