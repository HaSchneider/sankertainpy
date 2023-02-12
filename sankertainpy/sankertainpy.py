import numpy as np
import plotly.graph_objects as go
import matplotlib

def cut_off_flows(result, label_list, cutoff):
    # Combine flows < cutoff to one node:
    total_score= np.mean(result['scores'][0])
    label_list.append('Activities< cutoff')
    upstream=len(label_list)-1
    label_list.append('Activities< cutoff downstream')
    downstream=len(label_list)-1

    for i, flow in enumerate(result['scores']):
        if abs(np.mean(flow))/abs(total_score) < cutoff:  
            if np.mean(flow) > 0:
                result['sources'][i]= upstream
            else:
                result['sources'][i]= downstream
    return(result, label_list)


def add_emissions(i, result, label_list, upstream, downstream):
    # 
    inp=0
    out=0
    for n, scr in enumerate(result['scores']):
        if result['sources'][n]== i:
            out= out + np.mean(scr)
            
        if result['targets'][n]== i:
            inp= inp+ np.mean(scr)

    if inp!=0 and out!= 0 and inp != out:
        
        if out > 0:
            result['scores'].append(out-inp)
            result['sources'].append(upstream)
            result['targets'].append(i)
        else:
            result['scores'].append(out-inp)
            result['sources'].append(downstream)
            result['targets'].append(i)


    return(result, label_list)


def calc_emissions(result, label_list):
    # iterate through nodes and link emissions to aditional node
    label_list.append('Emissions')
    upstream=len(label_list)-1
    label_list.append('Emissions downstream')
    downstream = len(label_list)-1
    result['nodes'][len(label_list)-1]= {'name':'Emissions'}
    
    for _, (i, _) in enumerate(result['nodes'].items()):
        result,label_list= add_emissions(i, result, label_list, upstream, downstream)
    
    return(result, label_list)

def calc_quantile_flows(result, cutoff):
    # Split flows with list of Monte Carlo results into different quantiles
    total_score= np.mean(result['scores'][0])
    cmap = matplotlib.cm.get_cmap('RdYlGn')
    cmap_basic = matplotlib.cm.get_cmap('Blues')
    quantiles= np.arange(0.1,0.9,0.1) 
    #neg_quantiles= np.arange(0.9,0.9,0.1)
    new_targets, new_sources, new_scores, colors=[], [], [], []    

    for i, flow in enumerate(result['scores']):
        if type(flow) == list and abs(np.mean(flow)/total_score) > cutoff:           
            if np.mean(flow) <= 0:
                act_quantiles=np.flip(quantiles)
            else:
                act_quantiles=quantiles

            old_qu_score = 0 #np.quantile(flow, 0.1)
            for n, qu in enumerate(act_quantiles):
                
                new_scores.append(np.quantile(flow, qu)- old_qu_score)
                new_targets.append(result['targets'][i])
                new_sources.append(result['sources'][i])
                if old_qu_score == 0:
                    colors.append('rgba'+str(cmap_basic(0.5,0.6)))
                else:
                    if np.mean(flow) <= 0:
                        colors.append('rgba'+str(cmap(qu,0.9)))
                    else:
                        colors.append('rgba'+str(cmap(1-qu,0.9)))
                
                old_qu_score=np.quantile(flow, qu)

        else: #Add flows without Monte Carlo results
            new_scores.append(np.mean(flow))
            new_targets.append(result['targets'][i])
            new_sources.append(result['sources'][i])
            colors.append('rgba'+str(cmap_basic(0.5,0.6)))
    new_result={'targets':new_targets, 'sources':new_sources, 'scores':new_scores, 'nodes':result['nodes'],'colors':colors}
    return(new_result)
    

def calc_colors(result, cutoff):
    #
    total_score= np.mean(result['scores'][0])
    cmap_mc = matplotlib.cm.get_cmap('YlOrRd')
    cmap_smc = matplotlib.cm.get_cmap('Blues')
    
    max_std= max([np.std(fl) for fl in result['scores']])
    
    result['colors']=[0]*len(result['scores'])
    
    for i, flow in enumerate(result['scores']):
        if type(flow) == list and np.mean(flow)/total_score > cutoff:    
            scale=  round(np.std(flow)/max_std, 2) 
            color= cmap_mc(scale,0.9)
            new_color=[]
            # 
            for k in [0,1,2]:
                if color[k] ==1.0:
                    # workaround, because plotly prints the wrong color for "1.0" rgb values:
                    new_color.append(color[k]-0.000001)
                else:
                    new_color.append(color[k])
            new_color.append(0.9)
            color=tuple(new_color)

        else: #Add flows without Monte Carlo results
            color=cmap_smc(0.5,0.6)

        result['colors'][i]='rgba'+str(color)
        result['scores'][i] = np.mean(flow)
    return(result)

def flip_negativ_values(result):    
    for i, flow in enumerate(result['scores']):
        if flow <= 0:
            #p= result['targets'][i]
            #result['targets'][i]= result['sources'][i]
            #result['sources'][i]= p
            result['scores'][i]=abs(flow)

    return(result)

def adjust_result(result, type, cutoff, emission):
    label_list=[result['nodes'][nod]['name'] for nod in result['nodes']]
    
    result, label_list = cut_off_flows(result, label_list, cutoff)
    if emission:
        result, label_list = calc_emissions(result, label_list)
    
    if type ==1:
        result= calc_quantile_flows(result, cutoff)
    elif type ==0:
        result= calc_colors(result, cutoff)
    
    #flip negative values:
    result= flip_negativ_values(result)
    return(result, label_list)

def generate_sankey(result, type=1, cutoff= 0.05, emissions= True):
    '''
    Generate a plotly sankey figure with uncertainty. Made for visualizing LCA data from brightway2 activities. 
    
    Args:
        result= {
            'sources': list of int regarding the source nodes from 'nodes'
            'targets': list of int regarding the target nodes from 'nodes'
            'scores': list of floats/list containing the weight of the links between the nodes from 'nodes'. Monte Carlo results are wrapped in a nested list.
            'nodes': dictionary containing information about the nodes. Keys are int values.
        }
        type: int.  0 for visualize the uncertainty in form of colored intensity flows in relation to the standard deviation. Relativ to the highest standard deviation of the links.
                    1 for visualize the uncertainty by splitting each link in several links regarding theire quantiles with a color scale from low -green to high - red. 

        cutoff: float. Bundle links lower than cutoff value to one target node. 

        emissions: bool. activate or deactivate the emission links. They can be distracting if very low and not relevant.

    Background: https://doi.org/10.1016/j.cola.2019.03.002



    '''
    result, label_list = adjust_result(result, type, cutoff, emissions)    

    # style the figure:
    node_color=['grey']*len(label_list)
    node_color[0]='white'
    node_line=[dict(color = "black", width = 0.5)]*len(label_list)
    node_line[0]=dict(color = "white", width = 0.5)
    label_list[0]=''

    fig = go.Figure(data=[go.Sankey(
    node = dict(
      pad = 80,
      thickness = 20,
      line = dict(color = "black", width = 0.0),
      label = label_list,
      color = node_color,
    ),
    link = dict(
      source = result['sources'],
      target = result['targets'],
      value = result['scores'],
      color= result['colors'],
      arrowlen=10,
    ))])
    fig.update_layout(width=1400)
    fig.update_layout(height=800)
    #fig.update_layout(title_text="Basic Sankey Diagram", font_size=12)
    return(fig)
