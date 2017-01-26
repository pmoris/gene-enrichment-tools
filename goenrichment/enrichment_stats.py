#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: Pieter Moris
'''

import pandas as pd
import statsmodels.sandbox.stats.multicomp

from scipy.stats import hypergeom


# def enrichmentOneSided(GOid, background, subset, GOdict, gafDict, gafSubset, minGenes):
#     """
#     Performs a one-sided hypergeometric test for a given GO term.

#     Parameters
#     ----------
#     GOid : str
#         A GO identifier (key to the GO dictionary).
#     background : set of str
#         A set of background uniprot AC's.
#     subset : set of str
#         A subset of uniprot AC's of interest.
#     GOdict : dict
#         A dictionary of GO objects generated by importOBO().
#         Keys are of the format `GO-0000001` and map to OBO objects.
#     gafDict : dict
#         A dictionary mapping the background's gene uniprot AC's to GO ID's.
#     gafDict : dict
#         A dictionary mapping the subset's gene uniprot AC's to GO ID's.

#     Returns
#     -------
#     float
#         The p-value of the one-sided hypergeometric test.
#     """

#     backgroundTotal = len(background)
#     subsetTotal = len(subset)

#     validTerms = set([GOid])
#     validTerms.update(GOdict['GOid'].childs)

#     backgroundGO = countGOassociations(validTerms, gafDict)
#     subsetGO = countGOassociations(validTerms, gafDict)

#     # If the number of genes for the current GO category is too low, return 1
#     if backgroundGO < minGenes:
#         return None

#     # k or more successes (= GO associations = subsetGO) in N draws (= subsetTotal)
#     # from a population of size M (backgroundTotal) containing n successes (backgroundGO)
#     # k or more is the sum of the probability mass functions of k up to N successes
#     # since cdf gives the cumulative probability up and including input (less or equal to k successes),
#     # and we want P(k or more), we need to calculate 1 - P(less than k) =  1 - P(k-1 or less)
#     # .sf is the survival function (1-cdf).
#     pVal = hypergeom.sf(subsetGO - 1, backgroundTotal,
#                         backgroundGO, subsetTotal)

#     return pVal


def enrichmentOneSided(subsetGO, backgroundTotal, backgroundGO, subsetTotal):
    """
    Performs a one-sided hypergeometric test for a given GO term.

    k or more successes (= GO associations = subsetGO) in N draws (= subsetTotal)
    from a population of size M (backgroundTotal) containing n successes (backgroundGO)
    k or more is the sum of the probability mass functions of k up to N successes
    since cdf gives the cumulative probability up and including input (less or equal to k successes),
    and we want P(k or more), we need to calculate 1 - P(less than k) =  1 - P(k-1 or less)
    sf is the survival function (1-cdf).

    Parameters
    ----------
    GOid : str
        A GO identifier (key to the GO dictionary).
    backgroundTotal : int
        The total number of background uniprot AC's.
    subsetTotal : int
        The total number of subset uniprot AC's of interest.
    GOdict : dict
        A dictionary of GO objects generated by importOBO().
        Keys are of the format `GO-0000001` and map to OBO objects.
    gafDict : dict
        A dictionary mapping the background's gene uniprot AC's to GO ID's.        
    gafSubset : dict
        A dictionary mapping the subset's gene uniprot AC's to GO ID's.

    Returns
    -------
    float
        The p-value of the one-sided hypergeometric test.
    """

    pVal = hypergeom.sf(subsetGO - 1, backgroundTotal,
                        backgroundGO, subsetTotal)

    return pVal


def countGOassociations(validTerms, gaf):
    """
    """

    GOcounter = 0

    # For each gene:GO id set pair in the GAF dictionary
    for gene, GOids in gaf.items():
        # Increment the GO counter if the valid terms set shares a member
        # with the GO id set of the current gene
        if not validTerms.isdisjoint(GOids):
            GOcounter += 1

    return GOcounter


def enrichmentAnalysis(background, subset, GOdict, gafDict, gafSubset,
                       minGenes=3, threshold=0.05):

    # generate a list of all base GO id's to test
    # i.e. those of all genes in the subset of interest
    baseGOids = [GOid for gene, GOids in gafSubset.items()
                 for GOid in GOids if not GOdict[GOid].childs]

    # baseGOids = {gene:set() for gene in gafSubset}
    # for gene, GOids in gafSubset.items():
    #     for GOid in GOids:
    #         if not GOdict[GOid].childs:
    #             baseGOids[gene].add(GOid)
    # baseGOids = []
    # for gene, GOids in gafSubset.items():
    #     for GOid in GOids:
    #         if not GOdict[GOid].childs:
    #             baseGOids.append(GOid)

    pValues = {}

    backgroundTotal = len(background)
    subsetTotal = len(subset)

    # Perform a onesided enrichment test for each of the base GO id's,
    # Recurse to parents if not significant
    for GOid in baseGOids:

        recursiveTester(GOid, backgroundTotal, subsetTotal, GOdict,
                        gafDict, gafSubset, minGenes, threshold, pValues)

    return pValues


def recursiveTester(GOid, backgroundTotal, subsetTotal, GOdict, gafDict,
                    gafSubset, minGenes, threshold, pValues):

    # If a certain GOid already has a p-value stored,
    # it can be skipped and so can its parents
    if GOid not in pValues:

        # While testing for a term, also test all terms that were associated
        # with one of its childs
        validTerms = set([GOid])
        validTerms.update(GOdict[GOid].childs)

        # Count the number of genes in the background and subset that were
        # associated with the current terms
        backgroundGO = countGOassociations(validTerms, gafDict)
        subsetGO = countGOassociations(validTerms, gafSubset)

        # If the number of associated genes for the current GO category is too low,
        # skip and move up hierarchy to test the parents
        if backgroundGO < minGenes:
            for parent in GOdict[GOid].parents:
                recursiveTester(parent, backgroundTotal, subsetTotal,
                                GOdict, gafDict, gafSubset, minGenes,
                                threshold, pValues)

        else:
            # Map GOid to p-value
            pVal = enrichmentOneSided(
                subsetGO, backgroundTotal, backgroundGO, subsetTotal)
            pValues[GOid] = pVal

            # If test is not significant, move up the hierarchy to perform
            # additional tests on parent terms
            if pVal > threshold:
                for parent in GOdict[GOid].parents:
                    recursiveTester(parent, backgroundTotal, subsetTotal,
                                    GOdict, gafDict, gafSubset, minGenes,
                                    threshold, pValues)

            # Otherwise stop recursion and don't perform any higher up tests
            else:
                return


class goResults():

    def __init__(self):
        self.pValues = {}
        self.qValues = {}
        self.threshold = 0

    # def multipleTestingCorrection(self, threshold):
