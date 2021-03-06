import pandas as pd
import os
import csv
import numpy as np
import json
import sys
from typing import List, Dict, Tuple

"""
Created on Thu Apr 11 14:26:07 2019

@author: mh2210, Gabrielle Johnston, Benedict_Carling

"""

# Constant str
TEMPLATE_DIR_NAME = 'template_ot2_scripts'
CLIP_TEMP_FNAME = 'clip_template.py'
MAGBEAD_TEMP_FNAME = 'purification_template.py'
F_ASSEMBLY_TEMP_FNAME = 'assembly_template.py'
TRANS_SPOT_TEMP_FNAME = 'transformation_template.py'
THERMOCYCLE_TEMP_NAME = 'thermocycle_template.py'
CLIP_FNAME = '1_clip.ot2.py'
MAGBEAD_FNAME = '2_purification.ot2.py'
F_ASSEMBLY_FNAME = '3_assembly.ot2.py'
TRANS_SPOT_FNAME = '4_transformation.ot2.py'
THERMOCYCLE_FNAME = '1_5_thermocycle.ot2.py'
CLIPS_INFO_FNAME = 'clip_run_info.csv'
FINAL_ASSEMBLIES_INFO_FNAME = 'final_assembly_run_info.csv'
WELL_OUTPUT_FNAME = 'wells.txt'

# Constant floats/ints
CLIP_DEAD_VOL = 60
CLIP_VOL = 30
T4_BUFF_VOL = 3
BSAI_VOL = 1
T4_LIG_VOL = 0.5
CLIP_MAST_WATER = 15.5
PART_PER_CLIP = 200
MIN_VOL = 1
MAX_CONSTRUCTS = 96
MAX_CLIPS = 48
FINAL_ASSEMBLIES_PER_CLIP = 15
DEFAULT_PART_VOL = 1
MAX_SOURCE_PLATES = 6
MAX_FINAL_ASSEMBLY_TIPRACKS = 7
PART_DEAD_VOL = 15

# Constant dicts
SPOTTING_VOLS_DICT = {2: 5, 3: 5, 4: 5, 5: 5, 6: 5, 7: 5}

# Constant lists
# These are positions that the dna source plate can take
SOURCE_DECK_POS = ['2', '5', '8', '7', '10', '11']

# labware dictionary - filled in by front end
labware_dict = {'p10_mount': 'right', 'p300_mount': 'left',
                'p10_type': 'p10_single', 'p300_type': 'p300_multi',
                'well_plate': 'biorad_96_wellplate_200ul_pcr',
                'reagent_plate': 'usascientific_12_reservoir_22ml',
                'mag_plate': 'biorad_96_wellplate_200ul_pcr',
                'tube_rack': 'opentrons_24_tuberack_nest_1.5ml_snapcap',
                'aluminum_block':
                'opentrons_96_aluminumblock_biorad_wellplate_200ul',
                'bead_container': 'usascientific_96_wellplate_2.4ml_deep',
                'soc_plate': 'usascientific_96_wellplate_2.4ml_deep',
                'agar_plate': 'thermofisher_96_wellplate_180ul'}


def dnabot(
    output_folder: str, ethanol_well_for_stage_2: str,
    deep_well_plate_stage_4: str, input_construct_path: List[str],
    output_sources_paths: List[str],
    p10_mount: str = 'right',
    p300_mount: str = 'left',
    p10_type: str = 'p10_single',
    p300_type: str = 'p300_multi',
    well_plate: str = 'biorad_96_wellplate_200ul_pcr',
    reagent_plate: str = 'usascientific_12_reservoir_22ml',
    mag_plate: str = 'biorad_96_wellplate_200ul_pcr',
    tube_rack: str = 'opentrons_24_tuberack_nest_1.5ml_snapcap',
    aluminum_block: str = 'opentrons_96_aluminumblock_biorad_wellplate_200ul',
    bead_container: str = 'usascientific_96_wellplate_2.4ml_deep',
    soc_plate: str = 'usascientific_96_wellplate_2.4ml_deep',
    agar_plate: str = 'thermofisher_96_wellplate_180ul'
) -> List[str]:

    '''
        Main function, creates scripts and metainformation
        Can take specific args or just **labware_dict for all labware
        Args:
            output_folder: the full file path of the intended output folder
            for files generated
            ethanol_well_for_stage_2 = ethanol well in letter format e.g.
            'A1' to be used in purification
            deep_well_plate_stage_4 = soc well to be used in transformation
            please only enter wells from 'A1' to 'A12' as this is a trough
            construct_path: a one element list with the full path of the
            construct csv
            part_path: a list of full paths to part csv(s) (one or more)
            see labware_dict for rest of arguments

        Returns:
            List of output paths
            If there is an exception, the list of output paths will contain
            only one element = the error path
            Otherwise the list of output paths will contain:
            OT-2 script paths (clip, thermocycle, purification, assembly,
            transformation), metainformation (clip run info, final assembly
            dict, wells - ethanol well and soc well)
    '''
    # Parent directories
    generator_dir = os.getcwd()
    '''
        Ensure that template directories are correct.
        Important for running this script through the front end.
    '''
    if os.path.split(generator_dir)[1] == 'dna_bot':
        template_dir_path = os.path.join(generator_dir, TEMPLATE_DIR_NAME)
    elif os.path.split(generator_dir)[1] == 'basic_assembly':
        template_dir_path = os.path.join(generator_dir, 'dna_bot',
                                         TEMPLATE_DIR_NAME)
    else:
        template_dir_path = os.path.join(
            generator_dir, 'basic_assembly/dna_bot', TEMPLATE_DIR_NAME)
    full_output_path = output_folder

    '''In case construct path is list: can only have one path
       In future more than one construct plate could be allowed,
       but given that the well plate has 96 wells already this is
       not a priority.
    '''
    if type(input_construct_path) == list:
        input_construct_path = input_construct_path[0]

    construct_base = os.path.basename(input_construct_path)
    construct_base = os.path.splitext(construct_base)[0]

    all_my_output_paths = []

    try:
        constructs_list = generate_constructs_list(input_construct_path)
        clips_df = generate_clips_df(constructs_list)
        sources_dict, parts_df = generate_sources_dict(output_sources_paths)
        parts_df_temp = fill_parts_df(clips_df, parts_df)
        parts_df = parts_df_temp.copy()

        # calculate OT2 script variables
        clips_dict = generate_clips_dict(clips_df, sources_dict, parts_df)
        magbead_sample_number = clips_df['number'].sum()
        final_assembly_dict, clips_df, parts_df = generate_final_assembly_dict(
            constructs_list, clips_df, parts_df)
        final_assembly_tipracks = calculate_final_assembly_tipracks(
            final_assembly_dict)
        spotting_tuples = generate_spotting_tuples(constructs_list,
                                                   SPOTTING_VOLS_DICT)

        # check if p300_single (1 channel) or p300_multi (8 channel)
        if 'multi' in p300_type.lower():
            multi = True
        else:
            multi = False

        # Write OT2 scripts
        out_full_path_1 = generate_ot2_script(
            full_output_path, CLIP_FNAME,
            os.path.join(template_dir_path, CLIP_TEMP_FNAME),
            clips_dict=clips_dict,
            p10_mount=p10_mount, p10_type=p10_type, well_plate_type=well_plate,
            tube_rack_type=tube_rack)

        out_full_path_2 = generate_ot2_script(
            full_output_path, MAGBEAD_FNAME,
            os.path.join(template_dir_path, MAGBEAD_TEMP_FNAME),
            p300_mount=p300_mount,
            p300_type=p300_type, well_plate_type=well_plate,
            reagent_plate_type=reagent_plate,
            multi=multi, bead_container_type=bead_container,
            sample_number=magbead_sample_number,
            ethanol_well=ethanol_well_for_stage_2)

        out_full_path_3 = generate_ot2_script(
            full_output_path, F_ASSEMBLY_FNAME,
            os.path.join(template_dir_path, F_ASSEMBLY_TEMP_FNAME),
            final_assembly_dict=final_assembly_dict,
            tiprack_num=final_assembly_tipracks,
            p10_mount=p10_mount, p10_type=p10_type, mag_plate_type=mag_plate,
            tube_rack_type=tube_rack, aluminum_block_type=aluminum_block)

        out_full_path_4 = generate_ot2_script(
            full_output_path, TRANS_SPOT_FNAME,
            os.path.join(template_dir_path, TRANS_SPOT_TEMP_FNAME),
            spotting_tuples=spotting_tuples, soc_well=deep_well_plate_stage_4,
            p10_mount=p10_mount,
            p300_mount=p300_mount, p10_type=p10_type, p300_type=p300_type,
            well_plate_type=well_plate, tube_rack_type=tube_rack,
            soc_plate_type=soc_plate, agar_plate_type=agar_plate)

        # optional thermocycling script; run between clip reactions and
        # purification
        # requires the thermocycler module
        out_full_path_5 = generate_ot2_script(
            full_output_path, THERMOCYCLE_FNAME, 
            os.path.join(template_dir_path, THERMOCYCLE_TEMP_NAME),
            well_plate_type=well_plate)

        all_my_output_paths.append(out_full_path_1)
        all_my_output_paths.append(out_full_path_2)
        all_my_output_paths.append(out_full_path_3)
        all_my_output_paths.append(out_full_path_4)
        all_my_output_paths.append(out_full_path_5)

        # Write non-OT2 scripts - metainformation
        os.chdir(generator_dir)

        my_meta_dir = os.path.join(full_output_path, 'metainformation')
        if not os.path.exists(my_meta_dir):
            os.chdir(full_output_path)
            os.makedirs(my_meta_dir)
        os.chdir(my_meta_dir)

        # create master mix dataframe so that users know proportions
        master_mix_df = generate_master_mix_df(clips_df['number'].sum())

        # give information on source paths
        sources_paths_df = generate_sources_paths_df(
            output_sources_paths, SOURCE_DECK_POS)

        # create labware dataframe from labware_dict
        labwareDf = pd.DataFrame(
            data={'name': list(labware_dict.keys()),
                  'definition': list(labware_dict.values())})

        # save dfs as csv
        dfs_to_csv(construct_base + '_' + CLIPS_INFO_FNAME, index=False,
                   MASTER_MIX=master_mix_df, SOURCE_PLATES=sources_paths_df,
                   CLIP_REACTIONS=clips_df, PART_INFO=parts_df,
                   LABWARE=labwareDf)
        output_sources_paths.append(os.path.join(
            my_meta_dir, construct_base + '_' + CLIPS_INFO_FNAME))
        # final assembly dictionary - from original dnabot
        with open(construct_base + '_' + FINAL_ASSEMBLIES_INFO_FNAME,
                  'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for final_assembly_well, construct_clips in final_assembly_dict.items():
                csvwriter.writerow([final_assembly_well, construct_clips])
        output_sources_paths.append(os.path.join(
            my_meta_dir, construct_base + '_' + FINAL_ASSEMBLIES_INFO_FNAME))

        # additional well info - from original dnabot
        with open(construct_base + '_' + WELL_OUTPUT_FNAME, 'w') as f:
            f.write('Magbead ethanol well: {}'.format(ethanol_well_for_stage_2))
            f.write('\n')
            f.write('SOC column: {}'.format(deep_well_plate_stage_4))
        output_sources_paths.append(os.path.join(
            my_meta_dir, construct_base + '_' + WELL_OUTPUT_FNAME))
        os.chdir(generator_dir)

    except Exception as e:
        # write error to file in case of failure
        error_path = os.path.join(full_output_path, 'BASIC_error.txt')
        with open(error_path) as f:
            f.write("Failed to generate BASIC scripts: {}\n".format(str(e)))
        all_my_output_paths.append(error_path)

    finally:
        # return the paths of the outputs
        # changed to output_paths for consistency with other assembly methods
        output_paths = all_my_output_paths
        return output_paths


def generate_constructs_list(
    path: str
) -> List[pd.DataFrame]:
    """
        Generates a list of dataframes corresponding to each construct. Each
        dataframe lists components of the CLIP reactions required.
        Args: path = the absolute path of the constructs file
        Returns: List of dataframes, in which each dataframe = construct
    """

    def process_construct(construct):
        """Processes an individual construct into a dataframe of CLIP reactions
        outlining prefix linkers, parts and suffix linkers.

        """

        def interogate_linker(linker):
            """Interogates linker to determine if the suffix linker is a UTR
            linker.

            """
            if len(linker) >= 4:
                if linker[:3] == 'UTR':
                    return linker[:4] + '-S'
                return linker + '-S'
            else:
                return linker + '-S'

        clips_info = {'prefixes': [], 'parts': [],
                      'suffixes': []}
        for i, sequence in enumerate(construct):
            if i % 2 != 0:
                clips_info['parts'].append(sequence)
                clips_info['prefixes'].append(
                    construct[i - 1] + '-P')
                if i == len(construct) - 1:
                    suffix_linker = interogate_linker(construct[0])
                    clips_info['suffixes'].append(suffix_linker)
                else:
                    suffix_linker = interogate_linker(construct[i + 1])
                    clips_info['suffixes'].append(suffix_linker)
        return pd.DataFrame.from_dict(clips_info)

    constructs_list = []
    # myworkingd = os.getcwd()
    # print('my working directory {}'.format(myworkingd))
    with open(path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        for index, construct in enumerate(csv_reader):
            if index != 0:  # Checks if row is header.
                construct = list(filter(None, construct))
                if not construct[1:]:
                    break
                else:
                    constructs_list.append(process_construct(construct[1:]))

    # Errors
    if len(constructs_list) > MAX_CONSTRUCTS:
        raise ValueError(
            'Number of constructs exceeds maximum. Reduce construct number in construct.csv.')
    else:
        return constructs_list


def generate_clips_df(
    constructs_list: List[pd.DataFrame]
) -> pd.DataFrame:
    """
        Generates a dataframe containing information about all the unique clip
        reactions required to synthesise the constructs in constructs_list.
        Args: list of constructs stored as dataframes
        Returns: dataframe of all constructs
    """
    merged_construct_dfs = pd.concat(constructs_list, ignore_index=True)
    unique_clips_df = merged_construct_dfs.drop_duplicates()
    unique_clips_df = unique_clips_df.reset_index(drop=True)
    clips_df = unique_clips_df.copy()

    # Error
    if len(unique_clips_df.index) > MAX_CLIPS:
        raise ValueError(
            'Number of CLIP reactions exceeds 48. Reduce number of constructs in construct.csv.')

    # Count number of each CLIP reaction
    clip_count = np.zeros(len(clips_df.index))
    for i, unique_clip in unique_clips_df.iterrows():
        for _, clip in merged_construct_dfs.iterrows():
            if unique_clip.equals(clip):
                clip_count[i] = clip_count[i] + 1
    clip_count = clip_count // FINAL_ASSEMBLIES_PER_CLIP + 1
    clips_df['number'] = [int(i) for i in clip_count.tolist()]

    # Associate well/s for each CLIP reaction
    clips_df['clip_well'] = pd.Series(['0'] * len(clips_df.index),
                                      index=clips_df.index)
    clips_df['mag_well'] = pd.Series(['0'] * len(clips_df.index),
                                     index=clips_df.index)

    for index, number in clips_df['number'].iteritems():
        if index == 0:
            clip_wells = []
            mag_wells = []
            for x in range(number):
                clip_wells.append(final_well(x + 1))
                mag_wells.append(final_well(x + 1 + 48))
            clips_df.at[index, 'clip_well'] = tuple(clip_wells)
            clips_df.at[index, 'mag_well'] = tuple(mag_wells)
        else:
            clip_wells = []
            mag_wells = []
            for x in range(number):
                well_count = clips_df.loc[
                    :index - 1, 'number'].sum() + x + 1 + 48
                clip_wells.append(final_well(well_count - 48))
                mag_wells.append(final_well(well_count))
            clips_df.at[index, 'clip_well'] = tuple(clip_wells)
            clips_df.at[index, 'mag_well'] = tuple(mag_wells)
    return clips_df


def generate_sources_dict(
    paths: List[str]
) -> Tuple[Dict[str, Tuple], pd.DataFrame]:
    """Imports csvs files containing a series of parts/linkers with
    corresponding information into a dictionary where the key corresponds with
    part/linker and the value contains a tuple of corresponding information.

    Args:
        paths (list): list of strings each corresponding to a path for a
                      sources csv file.
    Returns:
        sources_dict: a dictionary with keys = part names, values = tuple of
        values - either well, concentration, plate or well, plate depending on
        whether concentration is provided for the part
        parts_df: dataframe of parts with cols = concentration, name, well,
        plate

    """
    sources_dict = {}
    part_dict = {}
    part_dict_list = []
    # print('my paths: {}'.format(paths))
    for deck_index, path in enumerate(paths):
        # print('my path: {}'.format(path))
        with open(path, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            for index, source in enumerate(csv_reader):
                if index != 0:
                    if len(source) > 2:
                        if source[2]:
                            csv_values = source[1:]
                            part_dict['concentration'] = [str(source[2])]
                        else:
                            csv_values = [source[1]]
                            part_dict['concentration'] = [PART_PER_CLIP]
                    else:
                        csv_values = [source[1]]
                        part_dict['concentration'] = [PART_PER_CLIP]
                    csv_values.append(SOURCE_DECK_POS[deck_index])
                    name = str(source[0])
                    if name.find('_Prefix') > 0:
                        index = name.index('Prefix')
                        if name[index-1] == '-':
                            name = name.replace('Prefix', 'P')
                        elif name[index-1] == '_':
                            name = name.replace('_Prefix', '-P')
                        else:
                            name = name.replace('Prefix', '-P')
                    elif 'Suffix' in name:
                        index = name.index('Suffix')
                        if name[index-1] == '-':
                            name = name.replace('Suffix', 'S')
                        elif name[index-1] == '_':
                            name = name.replace('_Suffix', '-S')
                        else:
                            name = name.replace('Suffix', '-S')
                    sources_dict[name] = tuple(csv_values)
                    part_dict['name'] = [name]
                    part_dict['well'] = [str(source[1])]
                    part_dict['plate'] = [SOURCE_DECK_POS[deck_index]]
                    part_dict_list.append(pd.DataFrame.from_dict(part_dict))
    parts_df = pd.concat(part_dict_list, ignore_index=True)
    # print('essential: {}'.format(sources_dict))
    return sources_dict, parts_df


def fill_parts_df(
    clips_df: pd.DataFrame,
    parts_df_temp: pd.DataFrame
) -> pd.DataFrame:
    """Fill dataframe of parts with metainformation to be stored in csv.
       Will add final assembly well in generate_final_assembly_dict()
       Args:
          clips_df: the dataframe of clips created as intermediate steps
          before assembly
          parts_df_temp: the previous parts_df dataframe to be expanded on
       Returns:
          parts_df, with new columns of 'clip_well', 'mag_well', 'total_vol',
          'vol_per_clip', and 'number'
    """
    parts_df = parts_df_temp.copy()

    # Create new columns and fill with dummy value '0'
    # 'clip_well' = the clip reaction wells the part will go into
    parts_df['clip_well'] = pd.Series(['0'] * len(parts_df.index),
                                      index=parts_df.index)
    # 'mag_well' = the purification wells the part will go into as
    # part of a clip
    parts_df['mag_well'] = pd.Series(['0'] * len(parts_df.index),
                                     index=parts_df.index)
    # 'total_vol' = the total volume of part, compensating for dead volume
    parts_df['total_vol'] = pd.Series(['0'] * len(parts_df.index),
                                      index=parts_df.index)
    # 'vol_per_clip' = the volume of the part needed per clip it is in
    parts_df['vol_per_clip'] = pd.Series(['0'] * len(parts_df.index),
                                         index=parts_df.index)
    # 'number' = the number of clips that the part will go in
    parts_df['number'] = pd.Series(['0'] * len(parts_df.index),
                                   index=parts_df.index)

    # Iterate through clips dataframe
    for index, row in clips_df.iterrows():
        # find clip indices in parts_df
        prefix_index = parts_df[
                parts_df['name'] == row['prefixes']].index.values[0]
        part_index = parts_df[
                parts_df['name'] == row['parts']].index.values[0]
        suffix_index = parts_df[
                parts_df['name'] == row['suffixes']].index.values[0]

        # fill 'clip_well', checking for dummy value
        if parts_df.at[prefix_index, 'clip_well'] == '0':
            parts_df.at[prefix_index, 'clip_well'] = list(row['clip_well'])
        else:
            parts_df.at[
                prefix_index, 'clip_well'].extend(list(row['clip_well']))
        if parts_df.at[part_index, 'clip_well'] == '0':
            parts_df.at[part_index, 'clip_well'] = list(row['clip_well'])
        else:
            parts_df.at[
                part_index, 'clip_well'].extend(list(row['clip_well']))
        if parts_df.at[suffix_index, 'clip_well'] == '0':
            parts_df.at[suffix_index, 'clip_well'] = list(row['clip_well'])
        else:
            parts_df.at[
                suffix_index, 'clip_well'].extend(list(row['clip_well']))

        # fill 'mag_well', checking for dummy value
        if parts_df.at[prefix_index, 'mag_well'] == '0':
            parts_df.at[prefix_index, 'mag_well'] = list(row['mag_well'])
        else:
            parts_df.at[
                prefix_index, 'mag_well'].extend(list(row['mag_well']))
        if parts_df.at[part_index, 'mag_well'] == '0':
            parts_df.at[part_index, 'mag_well'] = list(row['mag_well'])
        else:
            parts_df.at[
                part_index, 'mag_well'].extend(list(row['mag_well']))
        if parts_df.at[suffix_index, 'mag_well'] == '0':
            parts_df.at[suffix_index, 'mag_well'] = list(row['mag_well'])
        else:
            parts_df.at[
                suffix_index, 'mag_well'].extend(list(row['mag_well']))

        # fill number column
        parts_df.at[prefix_index, 'number'] = int(
            parts_df.at[prefix_index, 'number']) + int(row['number'])
        parts_df.at[part_index, 'number'] = int(
            parts_df.at[part_index, 'number']) + int(row['number'])
        parts_df.at[suffix_index, 'number'] = int(
            parts_df.at[suffix_index, 'number']) + int(row['number'])

    # iterate through parts dataframe to fill 'vol_per_clip' and 'total_vol'
    for index, row in parts_df.iterrows():
        noClips = int(row['number'])
        # check if prefix or suffix: volume = 1 uL
        if row['name'][len(row['name'])-2:len(row['name'])-1] == '-P':
            vol_per_clip = 1
        elif row['name'][len(row['name'])-2:len(row['name'])-1] == '-S':
            vol_per_clip = 1
        else:
            vol_per_clip = int(round(
                    PART_PER_CLIP / float(row['concentration']), 1))
            if vol_per_clip < MIN_VOL:
                vol_per_clip = MIN_VOL
        parts_df.at[index, 'vol_per_clip'] = vol_per_clip
        if noClips > 0:
            parts_df.at[index, 'total_vol'] = vol_per_clip*noClips + \
                PART_DEAD_VOL
        else:
            parts_df.at[index, 'total_vol'] = 0

    return parts_df


def generate_clips_dict(
    clips_df: pd.DataFrame,
    sources_dict: Dict[str, Tuple],
    parts_df: pd.DataFrame
) -> Dict[str, List]:
    """
        Using clips_df and sources_dict, returns a clips_dict which acts as the
        sole variable for the opentrons script "clip.ot2.py".
        Args:
            clips_df: dataframe of clip reactions
            sources_dict: dictionary of parts with csv values as keys
            parts_df: dataframe of parts
        Returns:
            clips_dict: dictionary to be used by 1_clip.ot2.py
    """
    max_part_vol = CLIP_VOL - (T4_BUFF_VOL + BSAI_VOL + T4_LIG_VOL
                               + CLIP_MAST_WATER + 2)
    clips_dict = {'prefixes_wells': [], 'prefixes_plates': [],
                  'suffixes_wells': [], 'suffixes_plates': [],
                  'parts_wells': [], 'parts_plates': [], 'parts_vols': [],
                  'water_vols': []}
    # Generate clips_dict from args
    try:
        for _, clip_info in clips_df.iterrows():
            prefix_linker = clip_info['prefixes']
            clips_dict['prefixes_wells'].append(
                [sources_dict[prefix_linker][0]]*clip_info['number'])
            clips_dict['prefixes_plates'].append([handle_2_columns(
                sources_dict[prefix_linker])[2]]*clip_info['number'])
            suffix_linker = clip_info['suffixes']
            clips_dict['suffixes_wells'].append(
                [sources_dict[suffix_linker][0]]*clip_info['number'])
            clips_dict['suffixes_plates'].append(
                [handle_2_columns(
                    sources_dict[suffix_linker])[2]]*clip_info['number'])
            part = clip_info['parts']
            clips_dict['parts_wells'].append([sources_dict[part][0]]
                                                * clip_info['number'])
            clips_dict['parts_plates'].append([handle_2_columns(
                sources_dict[part])[2]]*clip_info['number'])
            part_index = parts_df[parts_df['name'] == part].index.values[0]
            part_concentration = parts_df.at[part_index, 'concentration']
            if part_concentration != PART_PER_CLIP:
                part_vol = round(
                    PART_PER_CLIP / float(sources_dict[part][1]), 1)
                if part_vol < MIN_VOL:
                    part_vol = MIN_VOL
                elif part_vol > max_part_vol:
                    part_vol = max_part_vol
                water_vol = max_part_vol - part_vol
                clips_dict['parts_vols'].append(
                    [part_vol] * clip_info['number'])
                clips_dict['water_vols'].append(
                    [water_vol] * clip_info['number'])
            else:
                clips_dict['parts_vols'].append([DEFAULT_PART_VOL] *
                                                clip_info['number'])
                clips_dict['water_vols'].append(
                    [max_part_vol - DEFAULT_PART_VOL]*clip_info['number'])

    except KeyError:
        sys.exit('likely part/linker not listed in sources.csv')
    for key, value in clips_dict.items():
        clips_dict[key] = [item for sublist in value for item in sublist]
    return clips_dict


def generate_final_assembly_dict(
    constructs_list: pd.DataFrame,
    clips_df: pd.DataFrame,
    parts_df: pd.DataFrame
) -> Tuple[Dict[str, List[str]], pd.DataFrame, pd.DataFrame]:
    """
        Using constructs_list and clips_df, returns a dictionary of final
        assemblies with keys defining destination plate well positions and
        values indicating which clip reaction wells are used.
        Args:
            constructs_list: list of constructs, constructs = dataframes
            clips_df: dataframe of clip reactions
            parts_df: dataframe of parts
        Returns:
            dictionary of final assemblies with keys = destination plate,
            values = list of clip wells
            clips_df and parts_df updated with construct well column
    """
    final_assembly_dict = {}
    clips_count = np.zeros(len(clips_df.index))
    parts_df['construct_well'] = pd.Series(['0'] * len(parts_df.index),
                                           index=parts_df.index)
    clips_df['construct_well'] = pd.Series(['0'] * len(clips_df.index),
                                           index=clips_df.index)
    for construct_index, construct_df in enumerate(constructs_list):
        construct_well_list = []
        for _, clip in construct_df.iterrows():
            clip_info = clips_df[(clips_df['prefixes'] == clip['prefixes']) &
                                 (clips_df['parts'] == clip['parts']) &
                                 (clips_df['suffixes'] == clip['suffixes'])]
            clip_wells = clip_info.at[clip_info.index[0], 'mag_well']
            clip_num = int(clip_info.index[0])
            clip_well = clip_wells[int(clips_count[clip_num] //
                                       FINAL_ASSEMBLIES_PER_CLIP)]
            clips_count[clip_num] = clips_count[clip_num] + 1
            construct_well_list.append(clip_well)
            if clips_df.at[clip_num, 'construct_well'] == '0':
                clips_df.at[clip_num, 'construct_well'] = [str(
                    final_well(construct_index + 1))]
            else:
                clips_df.at[clip_num, 'construct_well'].append(str(
                    final_well(construct_index + 1)))
            prefix_index = parts_df[
                parts_df['name'] == clip['prefixes']].index.values[0]
            part_index = parts_df[
                parts_df['name'] == clip['parts']].index.values[0]
            suffix_index = parts_df[
                parts_df['name'] == clip['suffixes']].index.values[0]

            if parts_df.at[prefix_index, 'construct_well'] == '0':
                parts_df.at[prefix_index, 'construct_well'] = [str(
                    final_well(construct_index + 1))]
            else:
                parts_df.at[prefix_index, 'construct_well'].append(str(
                    final_well(construct_index + 1)))
            if parts_df.at[part_index, 'construct_well'] == '0':
                parts_df.at[part_index, 'construct_well'] = [str(
                    final_well(construct_index + 1))]
            else:
                parts_df.at[part_index, 'construct_well'].append(str(
                    final_well(construct_index + 1)))
            if parts_df.at[suffix_index, 'construct_well'] == '0':
                parts_df.at[suffix_index, 'construct_well'] = [str(
                    final_well(construct_index + 1))]
            else:
                parts_df.at[suffix_index, 'construct_well'].append(str(
                    final_well(construct_index + 1)))

        final_assembly_dict[final_well(
            construct_index + 1)] = construct_well_list

    return final_assembly_dict, clips_df, parts_df


def calculate_final_assembly_tipracks(
    final_assembly_dict: Dict[str, List[str]]
) -> int:
    """
        Calculates the number of final assembly tipracks required ensuring
        no more than MAX_FINAL_ASSEMBLY_TIPRACKS are used.
        Args: final_assembly_dict = dictionary with keys = final assembly
        wells, values = list of clip wells
        Returns: number of tipracks needed in final assembly
        (3_assembly.ot2.py)
        Raises: ValueError if final assembly tiprack number > tiprack slots

    """
    final_assembly_lens = []
    for values in final_assembly_dict.values():
        final_assembly_lens.append(len(values))
    master_mix_tips = len(list(set(final_assembly_lens)))
    total_tips = master_mix_tips + sum(final_assembly_lens)
    final_assembly_tipracks = total_tips // 96 + (
        1 if total_tips % 96 > 0 else 0)
    if final_assembly_tipracks > MAX_FINAL_ASSEMBLY_TIPRACKS:
        raise ValueError(
            'Final assembly tiprack number exceeds number of slots. Reduce number of constructs in constructs.csv')
    else:
        return final_assembly_tipracks


def generate_spotting_tuples(
    constructs_list: List[pd.DataFrame],
    spotting_vols_dict: Dict[int, int]
) -> List[Tuple]:
    """Using constructs_list, generates a spotting tuple
    (Refer to 'transformation_spotting_template.py') for every column of 
    constructs, assuming the 1st construct is located in well A1 and wells
    increase linearly. Target wells locations are equivalent to construct well
    locations and spotting volumes are defined by spotting_vols_dict.

    Args:
        spotting_vols_dict (dict): Part number defined by keys, spotting
            volumes defined by corresponding value.
    Returns:
        List of three tuples as instructions for transformation script
    """
    # Calculate wells and volumes
    wells = [final_well(x + 1) for x in range(len(constructs_list))]
    vols = [SPOTTING_VOLS_DICT[len(construct_df.index)]
            for construct_df in constructs_list]

    # Package spotting tuples
    spotting_tuple_num = len(constructs_list)//8 + (1
                                                    if len(constructs_list) % 8 > 0 else 0)
    spotting_tuples = []
    for x in range(spotting_tuple_num):
        if x == spotting_tuple_num - 1:
            tuple_wells = tuple(wells[8*x:])
            tuple_vols = tuple(vols[8*x:])
        else:
            tuple_wells = tuple(wells[8*x:8*x + 8])
            tuple_vols = tuple(vols[8*x:8*x + 8])
        spotting_tuples.append((tuple_wells, tuple_wells, tuple_vols))
    return spotting_tuples


def generate_ot2_script(parent_dir, ot2_script_path, template_path, **kwargs):
    """Generates an ot2 script named 'ot2_script_path', where kwargs are
    written as global variables at the top of the script. For each kwarg, the
    keyword defines the variable name while the value defines the name of the
    variable. The remainder of template file is subsequently written below.
    Args:
        parent_dir (str): output folder dir
        ot2_script_path (str): where the script should be saved, relative to
        the parent_dir
        template_path (str): where the template script can be found
    Returns:
        absolute path of script (str)
    """
    working_directory = os.getcwd()

    os.chdir(parent_dir)
    full_file_path = os.path.join(parent_dir, ot2_script_path)

    this_object_output_path = os.path.realpath(full_file_path)

    with open(ot2_script_path, 'w') as wf:
        with open(template_path, 'r') as rf:
            for index, line in enumerate(rf):
                if line[:3] == 'def':
                    function_start = index
                    break
                else:
                    wf.write(line)
            for key, value in kwargs.items():
                wf.write('{}='.format(key))
                if type(value) == dict:
                    wf.write(json.dumps(value))
                elif type(value) == str:
                    wf.write("'{}'".format(value))
                else:
                    wf.write(str(value))
                wf.write('\n')
            wf.write('\n')
        with open(template_path, 'r') as rf:
            for index, line in enumerate(rf):
                if index >= function_start - 1:
                    wf.write(line)

    os.chdir(working_directory)
    return this_object_output_path


def generate_master_mix_df(
    clip_number: int
) -> pd.DataFrame:
    """
        Generates a dataframe detailing the components required in the clip
        reaction master mix.
        Args: Number of clips needed in total
        Returns: master mix dataframe containing reagents + volumes
    """
    COMPONENTS = {'Component': ['Promega T4 DNA Ligase buffer, 10X',
                                'Water', 'NEB BsaI-HFv2',
                                'Promega T4 DNA Ligase']}
    VOL_COLUMN = 'Volume (uL)'
    master_mix_df = pd.DataFrame.from_dict(COMPONENTS)
    master_mix_df[VOL_COLUMN] = (clip_number + CLIP_DEAD_VOL/CLIP_VOL) * \
        np.array([T4_BUFF_VOL,
                  CLIP_MAST_WATER,
                  BSAI_VOL,
                  T4_LIG_VOL])
    return master_mix_df


def generate_sources_paths_df(
    paths: List[str], deck_positions: List[str]
) -> pd.DataFrame:
    """Generates a dataframe detailing source plate information.

    Args:
        paths (list): list of strings specifying paths to source plates.
        deck_positions (list): list of strings specifying candidate deck
        positions.
    Returns:
        Dataframe containing source plate information

    """
    source_plates_dict = {'Deck position': [], 'Source plate': [], 'Path': []}
    for index, path in enumerate(paths):
        source_plates_dict['Deck position'].append(SOURCE_DECK_POS[index])
        source_plates_dict['Source plate'].append(os.path.basename(path))
        source_plates_dict['Path'].append(path)
    return pd.DataFrame(source_plates_dict)


def dfs_to_csv(path, index=True, **kw_dfs):
    """Generates a csv file defined by path, where kw_dfs are
    written one after another with each key acting as a title. If index=True,
    df indexes are written to the csv file.

    """
    with open(path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        for key, value in kw_dfs.items():
            csvwriter.writerow([str(key)])
            value.to_csv(csvfile, index=index)
            csvwriter.writerow('')


def handle_2_columns(datalist):
    """This function has the intent of changing:
    ('A8', '2') => ('A8', '', '2')
    ('A8', '', '2') => ('A8', '', '2')
    [('E2', '5')] => [('E2', '', '5')]
    [('G1', '', '5')] => [('G1', '', '5')]
    with the purpose of handling 2 column csv part file inputs,
    as at times when 2 column csv files are input it creates tuples
    of length 2 instead of 3
    """
    return_list = 0
    if isinstance(datalist, list):
        datalist = datalist[0]
        return_list = 1
    if len(datalist) == 2:
        datalist = list(datalist)
        datalist.insert(1, "")
        datalist = tuple(datalist)
    if return_list:
        mylist = [""]
        mylist[0] = datalist
        return mylist
    return datalist


def final_well(
    sample_number: int
) -> str:
    """Determines well containing the final sample from sample number.
        Args: sample_number = integer, e.g. 0 = well index
        Returns: well in string form, e.g. 'A1' if sample_number = 0
    """
    letter = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    final_well_column = sample_number // 8 + \
        (1 if sample_number % 8 > 0 else 0)
    final_well_row = letter[sample_number - (final_well_column - 1) * 8 - 1]
    return final_well_row + str(final_well_column)


'''
Below is an example of how this would be run through the command line:
To use this, replace the output_folder name, construct_path, and part_paths.
'''
'''
output_folder_name = 'C:/Users/gabri/Documents/Uni/iGEM/DJANGO-Assembly-Methods/output'
ethanol_well = 'A11'
deep_well = 'A1'
construct_path = ["C:/Users/gabri/Documents/Uni/iGEM/DJANGO-Assembly-Methods/20201014_14_57_16/construct.csv"]
part_paths = ["C:/Users/gabri/Documents/Uni/iGEM/DJANGO-Assembly-Methods/20201014_14_57_16/part_linker_1.csv"]

dnabot(output_folder_name, ethanol_well, deep_well, construct_path, part_paths,
       **labware_dict)

'''
