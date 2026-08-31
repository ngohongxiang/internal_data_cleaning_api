r"""
---Suggestions on the Usage of clean_main() on Anvil Uplink Notebook---
Use the code sample below (RECOMMENDED) after the code that converts the 4 date columns to a datetime object on Anvii Uplink Notebook:
df = clean_df(df)

Note: NO CHANGES to the code needed for subsequent runtime.

Alternatively, you can choose to save the cleaned df to CSV (if you pass the 2nd positional argument as True) with the code below:
clean_df(df, is_csv=True)
df = pd.read_csv('eventbrite-dataset-anonymised-final.csv')

Note: If you intend to keep the CSV after the 1st generation (may have some ISSUES on 2nd run), replace your 1st pd.read_csv() with the code on the 2nd line above and disable cells that changes the data type for the 4 dates.

ABOVE codes are just SUGGESTIONS ONLY. For REFERENCE on USAGE.

---Public API(s)---
1) clean_df - data cleaning

Dependencies:
1) clean_df | Requires the latest Eventbrite CSV
""";

import numpy as np
import pandas as pd

import re

def _replace_multi(string, to_replace):
    '''
    to_replace : dict
    
    All keys in lower case. Each key matched at max once.
    '''
    for old_value, new_value in to_replace.items():
        if old_value in string:
            string = string.replace(old_value, new_value, 1)
    return string

def _value_reclassify(string, to_reclassify):
    '''
    to_reclassify : dict

    Each key matched at max once.
    '''
    for k, v in to_reclassify.items():
        if k in string:
            return v
    return ''

def _clean_location(df):
    #Assign location with value "0" to "Others". For exact_course_name does not contain "trip" and "Deep Learning" and "Free", classify them all under Online instead of others    
    return ['BT' * ('BT' in course or 'Bukit Timah' in course) or
            'TP' * ('Tamp' in course) +
            'MP' * (('MP' in course or 'Marine Parade' in course) and 'MP/' not in course) +
            'Bishan' * ('Bishan' in course) or
            'Others' * ('Deep Learning' in course or 'trip' in course or 'Free' in course and location == '0') or
            'Online' * ('Deep Learning' not in course or 'trip' not in course or 'Free' not in course and location == '0')
            for course, location in zip(df.exact_course_name, df.location)]

def _clean_course_name(df):
    to_reclassify1 = {'pygame': 'Pygame', 'level compu': 'O Level Computing', 'master c': 'Junior Master Class', '1(html': 'Web Programming 1', '2(html': 'Web Programming 2', 'basics1': 'Basics 1', '11-18yr': 'Python: Online Open House'}
    to_reclassify2 = {'principles+ 1': 'Principles 1', 'principles+ 2': 'Principles 2'}
    to_replace = {"(": "", ")": "", "- Design": "Design", "uting1": "uting 1", "e pro": "e Pro"}

    return [_value_reclassify(exact_course, to_reclassify1) +
            _value_reclassify(course.lower(), to_reclassify2) +
            f'Principles X: {_replace_multi(course[13:], to_replace)}' * ('principles x' in course.lower()) or
            course
            for exact_course, course in zip(df.exact_course_name.str.lower(), df.course_name.str.strip())]


def _clean_category(df):
    # Pygame --> Principles, Web Programming --> Principles, O Level Computing --> Academics, Junior Master Class --> Others
    return ['Principles' * ('pygame' in course_cleaned or 'b pro' in course_cleaned) +
            'Academics' * ('level compu' in course_cleaned) +
            'Others' * (('master c' in course_cleaned or 'n:' in course_cleaned) or (category == 'Workshop' or category == 'Trip')) +
            'Basics' * (course_cleaned == 'basics 1' and category == '0') or
            category
            for category, course_cleaned in zip(df.category, df.course_name.str.lower())]

def _clean_course_format(df):
    # 0, Trip, Workshop --> Camp, Weekly, Others
    # calculate course duration
    course_duration = (df.event_end_date - df.event_start_date).dt.days + 1

    # 0, Open House, Trip, Workshop --> Weekly, Camp, Others
    to_reclassify = ('0', 'Open House', 'Trip', 'Workshop')

    return ['Weekly' *  (duration > 30 and course_format in to_reclassify) +
            'Camp' * ((3 <= duration <= 30) and course_format in to_reclassify) +
            'Others' * (duration < 3 and course_format in to_reclassify) or
            course_format
            for course_format, duration in zip(df.course_format, course_duration)]

def _clean_get_transferred(df):
    dict_get_rev = {int(comment[-10:]): (gRev, tRev, pRev, gst, discount, order_id)
                    for comment, order_id, gRev, tRev, pRev, gst, discount
                    in zip(df.comments.astype(str), df.order_id, df.gross_revenue, df.ticket_revenue, df.pre_gst_revenue, df.gst, df.discount)
                    if 'to' in comment and gRev > 0}

    # fix those who transferred twice
    for k, v in ((2354525009, 2396800109), (2280444719, 2341088089), (1743961549, 1746635161)):
        if k in dict_get_rev:
            dict_get_rev[v] = dict_get_rev.pop(k)

    # fix: include add-on revenue
    if 1510937679 in dict_get_rev:
        dict_get_rev[1510937679] = (374.5, 342.26, 350, 24.5, 100, 1492386837)
    
    return dict_get_rev

def _clean_get_combo(df):
    to_find = 'j?p\d|[a-z]{5,9}s \da?'
    to_replace = {'jp': 'junior python ', 'p2': 'principles 2', 'p3': 'principles 3'}

    dict_get_combo = {buyer: [_replace_multi(course, to_replace) for course in re.findall(to_find, tClass)]
                      + [round(v / 2, 2) for v in (gRev, tRev, pRev, gst, discount)] + [order_id]
                      for tClass, order_id, buyer, course, gRev, tRev, pRev, gst, discount
                      in zip(df.ticket_class_name.str.lower(), df.order_id, df.anon_purchaser_name, df.course_name, df.gross_revenue, df.ticket_revenue, df.pre_gst_revenue, df.gst, df.discount)
                      if 'combo' in tClass and gRev > 0}

    # fix untraceable combo (1225494249) and 3 in 1 bundle
    for k in ('Oconnell Jones', 'Vervoort VI', 'Chase Heinrichs', 'Esparza Collins', 'Josette Hasegawa', 'Rodrigues Collins', 'Weeks Collins', 'Daly Dijkman'):
        if k in dict_get_combo:
            del dict_get_combo[k]

    # fix 3 in 1 bundle revenue
    if 'Mckinney Jansse' in dict_get_combo:
        dict_get_combo['Mckinney Jansse'] = ('junior python 2', 'junior python 3', 572.02, 520.9, 534.6, 37.42, 0, 2237974969)

    
    # set the revenues for the bundled purchase(s)
    dict_combo_zero = {order_id: (course, filtered[:2], buyer, *filtered[-6:-1])
                       for order_id, buyer, course, gRev
                       in zip(df.order_id, df.anon_purchaser_name, df.course_name, df.gross_revenue)
                       if course.lower() in (filtered := dict_get_combo.get(buyer, []))[:2] and gRev == 0}

    # fix duplicates
    for k in (1533758423, 2120811689, 3360052169):
        if k in dict_combo_zero:
            del dict_combo_zero[k]

    # fix: include add-on revenue, etc ('Vervoort VI', 'Chase Heinrichs', 'Esparza Collins', 'Josette Hasegawa', 'Rodrigues Collins', 'Weeks Collins', 'Daly Dijkman')
    for keys, revs in (((2214716149, 2214885299, 2214903969), (779.25, 714.57, 728.27, 50.98, 0)),
                       ((1733391209, 2099917209, 2105917479), (563.46, 512.77, 526.6, 36.86, 27)),
                       ((905513993, 912617002), (635, 618.13, 635, 0, 110)),
                       ((2169891889, 2169930699), (536.29, 488.18, 501.2, 35.09, 28)),
                       ((2170490549, 2170509139), (416.87, 379.37, 389.6, 27.27, 28)),
                       ((895584315, 897754702), (502.5, 488.94, 502.5, 0, 242.5)),
                       ((1334096134, 1334171400), (125, 121.38, 125, 0, 0)),
                       ((1334097328, 1334176398), (373, 363.18, 373, 0, 0))):
        for k in keys:
            if k in dict_combo_zero:
                dict_combo_zero[k] = ('Junior Python n', ('junior python 2', 'junior python 3'), 'name x', *revs)
    
    return dict_get_combo, dict_combo_zero

def _clean_transferred_combo(df):
    dict_get_rev = _clean_get_transferred(df[['comments', 'order_id', 'gross_revenue', 'ticket_revenue', 'pre_gst_revenue', 'gst', 'discount']])
    dict_get_combo, dict_combo_zero = _clean_get_combo(df[['ticket_class_name', 'order_id', 'anon_purchaser_name', 'course_name', 'gross_revenue', 'ticket_revenue', 'pre_gst_revenue', 'gst', 'discount']])
    
    # {move rev to transaction, set original transaction rev to 0, set original combo transaction rev, bundled transactions}
    dict_transferred_combo = {**{k: v[:-1] for k, v in dict_get_rev.items()}, **{v[-1]: [0] * 5 for v in dict_get_rev.values()},
                              **{v[-1]: v[-6:-1] for v in dict_get_combo.values()}, **{k: v[-5:] for k, v in dict_combo_zero.items()}}
    
    return np.array([dict_transferred_combo.get(order_id) or (gRev, tRev, pRev, gst, discount)
                     for order_id, gRev, tRev, pRev, gst, discount
                     in zip(df.order_id, df.gross_revenue, df.ticket_revenue, df.pre_gst_revenue, df.gst, df.discount)])

def clean_df(df):
    '''
    df : Eventbrite Pandas DataFrame object
    '''
    # early exit to avoid unnecessary work when input is unexpected
    if not isinstance(df, pd.DataFrame):
        raise TypeError('Input is not a pandas dataframe.')
    check_cols = ('exact_course_name', 'category', 'course_format', 'location', 'course_name', 'order_id', 'anon_purchaser_name', 'order_creation_date', 'event_created_date', 'event_start_date', 'event_end_date', 'gross_revenue', 'ticket_revenue', 'pre_gst_revenue', 'gst', 'discount', 'comments', 'ticket_class_name')
    if not set(check_cols).issubset(df):
        raise KeyError('Expected column(s) does not exist in dataframe.')
    
    # prevent reference to original df
    df = df.copy()
    
    df['location'] = _clean_location(df[['exact_course_name', 'location']])
    df['course_name'] = _clean_course_name(df[['exact_course_name', 'course_name']])
    df['category'] = _clean_category(df[['category', 'course_name']])    
    df['course_format'] = _clean_course_format(df[['course_format', *check_cols[9:11]]])
    
    df[[*check_cols[11:16]]] = _clean_transferred_combo(df[['comments', 'order_id', 'ticket_class_name', 'anon_purchaser_name', 'course_name', *check_cols[11:16]]])

    return df
