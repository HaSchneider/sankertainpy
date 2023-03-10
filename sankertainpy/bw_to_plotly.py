from warnings import warn
import bw2calc as bc
import numpy as np
from bw2data import get_activity

'''
Code based on recursive_calculation_to_object() from bwio package from brightway2!

'''

def recursive_calculation_to_plotly(
    activity,
    lcia_method,
    amount=1,
    max_level=3,
    cutoff=1e-2,
    mc=False,
    mc_number=100, 
    _lca_obj=None,
    _total_score=None,
    __result_list=None,
    __level=0,
    __nodes=None,
    __source = None,
    __target= None,
    __actual_node=None,
    __scores=None,
    __parent_node=None,

):
    """Traverse a supply chain graph, and calculate the LCA scores of each component. Adds a dictionary to ``result_list`` of the form:

       
    Args:
        activity: ``Activity``. The starting point of the supply chain graph.
        lcia_method: tuple. LCIA method to use when traversing supply chain graph.
        amount: int. Amount of ``activity`` to assess.
        max_level: int. Maximum depth to traverse.
        cutoff: float. Fraction of total score to use as cutoff when deciding whether to traverse deeper and if Monte Carlo simulation should be carried out.
        mc: bool. Decide if Monte Carlo simulation should carried out. This can take some time.
        mc_number: int. Iterations of the monte carlo simulations
    

    Internal args (used during recursion, do not touch):
        __result_list
        __level
        __nodes
        __source 
        __target
        __actual_node
        __scores
        __parent_node
        ...

    Returns:
        dictionary of the following lists:
            sources: list of int regarding the keys from 'nodes'
            targets: list of int regarding the keys from 'nodes'
            scores: list of floats/list containing the weight of the links between the nodes from 'nodes'. Monte Carlo results are wrapped in a nested list.
            nodes: dictionary containing information about the nodes. Keys are int values regarding the source/target values.

    """

    activity = get_activity(activity)
    if __nodes is None:
        __nodes={0:{"act":activity, 'name':f"{activity['name']}, {activity['location']}"}}
        __nodes[1]={"act":activity, 'name':f"{activity['name']}, {activity['location']}"}
        __actual_node=1
        __parent_node=0
        __source= []
        __target=[]
        __scores=[]
    else:
        __nodes[__actual_node]={"act":activity, 'name':f"{activity['name']}, {activity['location']}"}
    
    if _lca_obj is None:
        if mc:
            _lca_obj = bc.LCA({activity: amount}, lcia_method, use_distributions=True)
            _lca_obj.lci()
            _lca_obj.lcia()
            mc_result=[_lca_obj.score for _ in zip(range(mc_number), _lca_obj)]
            _total_score = np.median(mc_result)
            score= mc_result

        else:
            _lca_obj = bc.LCA({activity: amount}, lcia_method)
            _lca_obj.lci()
            _lca_obj.lcia()
            _total_score = _lca_obj.score
            score=_total_score 
        
    elif _total_score is None:
        raise ValueError
    else:
        if mc:
            _lca_obj.redo_lcia({activity.id: amount})
            score= _lca_obj.score
            if abs(score) > abs(_total_score * cutoff):
                _lca_obj.redo_lcia({activity.id: amount})
                score= [_lca_obj.score for _ in zip(range(mc_number), _lca_obj)]

        else:
            _lca_obj.redo_lcia({activity.id: amount})
            score= _lca_obj.score
        
    __target.append(__parent_node)
    __source.append(__actual_node)
    __scores.append(score)

    if __level < max_level and abs(_lca_obj.score) > abs(_total_score * cutoff):
        prod_exchanges = list(activity.production())
        if not prod_exchanges:
            prod_amount = 1
        elif len(prod_exchanges) > 1:
            warn(
                "Hit multiple production exchanges for {}; aborting in this branch".format(
                    activity
                )
            )
            return
        else:
            prod_amount = _lca_obj.technosphere_matrix[
                _lca_obj.dicts.product[prod_exchanges[0].input.id],
                _lca_obj.dicts.activity[prod_exchanges[0].output.id],
            ]
        actual_node_static = __actual_node

        for exc in activity.technosphere():
            if exc.input.id == exc.output.id:
                continue

            tm_amount = exc["amount"]

            __target, __source,__scores, __nodes, __actual_node=recursive_calculation_to_plotly(
                activity=exc.input,
                lcia_method=lcia_method,
                amount=amount * tm_amount / prod_amount,
                max_level=max_level,
                cutoff=cutoff,
                mc=mc,
                mc_number=mc_number,
                __result_list=__result_list,
                _lca_obj=_lca_obj,
                _total_score=_total_score,
                __level=__level + 1,
                __nodes=__nodes,
                __source = __source,
                __target = __target,
                __actual_node=__actual_node +1,
                __scores=__scores,
                __parent_node=actual_node_static,
            )
    if __level == 0:
        return({'targets':__target, 'sources':__source, 'scores':__scores, 'nodes':__nodes})
    else:
        return __target, __source,__scores, __nodes, __actual_node