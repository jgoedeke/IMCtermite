
import imctermite
import pandas
import datetime

def add_trigger_time(trigger_time, add_time) :
    trgts = datetime.datetime.strptime(trigger_time,'%Y-%m-%dT%H:%M:%S')
    dt = datetime.timedelta(seconds=add_time)
    return (trgts + dt).strftime('%Y-%m-%dT%H:%M:%S:%f')

if __name__ == "__main__" :

    # read file
    imctm = imctermite.ImcTermite("samples/exampleB.raw")
    
    # Get metadata only
    chns = imctm.get_channels(False)
    
    if not chns:
        print("No channels found")
        exit()
    
    # Prepare DataFrame
    df = pandas.DataFrame()

    # Get X-axis from the first channel
    first_chn = chns[0]
    
    data = imctm.get_channel_data(first_chn['uuid'], include_x=True)
    x_data = data['x']
    
    xcol = "time ["+first_chn['xunit']+"]"
    df[xcol] = x_data

    # sort channels by name
    chnnms = sorted([chn['name'] for chn in chns], reverse=False)
    chnsdict = {chn['name']: chn for chn in chns}

    for chnnm in chnnms :
        chn = chnsdict[chnnm]
        uuid = chn['uuid']
        
        # Fetch Y data only
        data = imctm.get_channel_data(uuid, include_x=False)
        y_data = data['y']
        
        ycol = chn['yname']+" ["+chn['yunit']+"]"
        
        # Assign to DataFrame
        if len(y_data) == len(df):
            df[ycol] = y_data
        else:
            # Fallback to Series for alignment/filling
            df[ycol] = pandas.Series(y_data)

    # show entire dataframe and write file
    print(df)
    df.to_csv("exampleB.csv",header=True,sep='\t',index=False)

