import pandas as pd
import pickle


standard_list = []
a = ""


def get_golden_master():
    golden_master = pd.read_pickle('./crc_dataframe1.pkl')
    return golden_master

def write_dataframe(dataframe):
    records = open("testDF.pkl", "wb")
    pickler = pickle.Pickler(records)
    pickler.dump(dataframe)
    records.close()


def create_gold_master(args):
    dict_to_df = {}
    for i in args:
        dict_to_df[i[0]] = i[1]

    dataframe = pd.DataFrame(dict_to_df.values(), index=dict_to_df.keys())

    #for k in dict_to_df.keys():
    #    print(k, dict_to_df[k])
    #print(type(dict_to_df))

    return dataframe


def check_gold_master(args, dataframe):
    indexvar = get_dataframe_index(dataframe)
    for entry in indexvar:
        if entry == args:
            localVar = entry
            break
    return dataframe.loc[localVar, 1]


def print_gold_master(dataframe):
    indexvar = get_dataframe_index(dataframe)
    #print(repr(indexvar.__dict__))
    #for entry in get_dataframe_index(dataframe):
    print(indexvar[1], dataframe.loc[indexvar[1], 1])


def get_dataframe_index(dataframe):
    return dataframe.index._index_data


def main(args):
    golden_master = create_gold_master([("a", [0, "first entry"]), ("b", [1, "second entry"])])
    print_gold_master(golden_master)
    write_dataframe(golden_master)
    #print(args, check_gold_master(args, golden_master))


if __name__ == '__main__':
    main("b")
