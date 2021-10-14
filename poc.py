import pandas as pd


standard_list = []
a = ""


def create_gold_master(args):
    """
    Function to create a sample pandas dataframe using the dictionary api
    to process args.
    """
    dict_to_df = {}
    for i in args:
        dict_to_df[i[0]] = i[1]

    dataframe = pd.DataFrame(dict_to_df.values(), index=dict_to_df.keys())

    #for k in dict_to_df.keys():
    #    print(k, dict_to_df[k])
    #print(type(dict_to_df))

    return dataframe


def check_gold_master(args, dataframe):
    """
    Function to check the value in the dictionary when a key is passed as a parameter in args.
    ** An assumption is made here that only one argument will be passed to main. **
    """
    indexvar = get_dataframe_index(dataframe)
    for entry in indexvar:
        if entry == args:
            localVar = entry
            break
    return dataframe.loc[localVar, 1]


def print_gold_master(dataframe):
    """
    Function used to print out values from the gold master.
    Used for debugging.
    """
    indexvar = get_dataframe_index(dataframe)

    # Note the use of repr (represent) here to find out what it contains and type
    print(repr(indexvar.index.__dict__))
    #for entry in get_dataframe_index(dataframe):
    print(indexvar[1], dataframe.loc[indexvar[1], 1])


def get_dataframe_index(dataframe):
    return dataframe.index._index_data


def main(args):
    golden_master = create_gold_master([("a", [0, "first entry"]), ("b", [1, "second entry"])])
    print_gold_master(golden_master)
    #print(args, check_gold_master(args, golden_master))


if __name__ == '__main__':
    main("b")
