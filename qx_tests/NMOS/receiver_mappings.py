import enum


@enum.unique
class DualMapping(enum.Enum):
    VID = {'Qx': "SFP A+B Rx:VID", 'QxL': "SFP E+F Rx:VID", 'QxP': "SFP E+F Rx:VID"}
    AUD1 = {'Qx': "SFP A+B Rx:AUD 1", 'QxL': "SFP E+F Rx:AUD 1", 'QxP': "SFP E+F Rx:AUD 1"}
    AUD2 = {'Qx': "SFP A+B Rx:AUD 2", 'QxL': "SFP E+F Rx:AUD 2", 'QxP': "SFP E+F Rx:AUD 2"}
    AUD3 = {'Qx': "SFP A+B Rx:AUD 3", 'QxL': "SFP E+F Rx:AUD 3", 'QxP': "SFP E+F Rx:AUD 3"}
    AUD4 = {'Qx': "SFP A+B Rx:AUD 4", 'QxL': "SFP E+F Rx:AUD 4", 'QxP': "SFP E+F Rx:AUD 4"}
    ANC = {'Qx': "SFP A+B Rx:ANC", 'QxL': "SFP E+F Rx:ANC", 'QxP': "SFP E+F Rx:ANC"}


@enum.unique
class SingleMapping(enum.Enum):
    VID_1 = {'Qx': "SFP A Rx:VID", 'QxL': "SFP E Rx:VID", 'QxP': "SFP E Rx:VID"}
    AUD1_1 = {'Qx': "SFP A Rx:AUD 1", 'QxL': "SFP E Rx:AUD 1", 'QxP': "SFP E Rx:AUD 1"}
    AUD2_1 = {'Qx': "SFP A Rx:AUD 2", 'QxL': "SFP E Rx:AUD 2", 'QxP': "SFP E Rx:AUD 2"}
    AUD3_1 = {'Qx': "SFP A Rx:AUD 3", 'QxL': "SFP E Rx:AUD 3", 'QxP': "SFP E Rx:AUD 3"}
    AUD4_1 = {'Qx': "SFP A Rx:AUD 4", 'QxL': "SFP E Rx:AUD 4", 'QxP': "SFP E Rx:AUD 4"}
    ANC_1 = {'Qx': "SFP A Rx:ANC", 'QxL': "SFP E Rx:ANC", 'QxP': "SFP E Rx:ANC"}
    VID_2 = {'Qx': "SFP B Rx:VID", 'QxL': "SFP F Rx:VID", 'QxP': "SFP F Rx:VID"}
    AUD1_2 = {'Qx': "SFP B Rx:AUD 1", 'QxL': "SFP F Rx:AUD 1", 'QxP': "SFP F Rx:AUD 1"}
    AUD2_2 = {'Qx': "SFP B Rx:AUD 2", 'QxL': "SFP F Rx:AUD 2", 'QxP': "SFP F Rx:AUD 2"}
    AUD3_2 = {'Qx': "SFP B Rx:AUD 3", 'QxL': "SFP F Rx:AUD 3", 'QxP': "SFP F Rx:AUD 3"}
    AUD4_2 = {'Qx': "SFP B Rx:AUD 4", 'QxL': "SFP F Rx:AUD 4", 'QxP': "SFP F Rx:AUD 4"}
    ANC_2 = {'Qx': "SFP B Rx:ANC", 'QxL': "SFP F Rx:ANC", 'QxP': "SFP F Rx:ANC"}
