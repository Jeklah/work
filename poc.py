import pandas as pd
import numpy as np
import pickle

standard_list = []
a = ""


def write_gold_master(dataframe):
    """
    Function to write the dataframe to pickle file to load in test file.
    """
    records = open("test_df.pkl", "wb")
    pickler = pickle.Pickler(records)
    pickler.dump(dataframe)
    records.close()

def create_gold_master(args):
    """
    Function to create a sample pandas dataframe using the dictionary api
    to process args.
    """
    dict_to_df = {}
    for i in args:
        dict_to_df[i[0]] = i[1]

    gold_master = pd.DataFrame(dict_to_df.values(), index=dict_to_df.keys(), columns=["column1", "column2"])

    #for k in dict_to_df.keys():
    #    print(k, dict_to_df[k])
    #print(type(dict_to_df))
    #gold_master = pd.DataFrame.from_dict(dict_to_df, orient='index', columns=['named column 1', 'named column 2'])

    return gold_master


def check_gold_master(args, dataframe):
    """
    Function to check the value in the dictionary when a key is passed as a parameter in args.
    ** An assumption is made here that only one argument will be passed to main. **
    """
    indexvar = get_dataframe_index(dataframe)
    for entry in indexvar:
        #print(f'{eval(entry)}')
        entry_index = np.where(indexvar=='eval(entry)')
        print(entry_index)
        if entry == args:
            localvar = entry
            #print(dataframe)
            print(f'indexvar: {indexvar[0]}')
            print(f'localvar: {localvar}')
            print(f'entry: {entry}')
            print(f'entry_index: {entry_index}')
            break
    #return dataframe.loc[localvar[entry_index]]


def print_gold_master(dataframe):
    """
    Function used to print out values from the gold master.
    Used for debugging.
    """
    indexvar = get_dataframe_index(dataframe)
    #print(repr(indexvar.__dict__))
    #for entry in get_dataframe_index(dataframe):
    print(indexvar[1], dataframe.loc[indexvar[1], 1])


def getataframe_index(dataframe):
    """
    Function to return the index
    """

    #print(args, check_gold_master(args, golden_master))

    # Note the use of repr (represent) here to find out what it contains and type
    #print(repr(indexvar))
    #for entry in get_dataframe_index(dataframe):
    #print(indexvar[1], dataframe.loc[indexvar[1], 1])
    #print(indexvar)
    #print(dataframe.loc[indexvar[0]])
    print(dataframe)

    #print(f'dataframe index data: {dataframe.index._index_data}')
    return dataframe.index._index_data


def main(args):
    #data = {"named row 1": ["first entry col1", "second entry col1"],
    #        "named row 2": ["first entry col2", "second entry col2"]}
    #golden_master = create_gold_master([("named row 1")])
    golden_master = create_gold_master([("named row 1", [ "first entry col1",  "second entry col1"]),
                                        ("named row 2", [ "first entry col2",  "second entry col2"])])
    #golden_master = create_gold_master([("a", [0, "first entry"]), ("b", [1, "second entry"])])
    print_gold_master(golden_master)
    print()
    write_gold_master(golden_master)
    print(f'Checking gold master: {check_gold_master(args, golden_master)}')

if __name__ == '__main__':
    main("named row 1")
