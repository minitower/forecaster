from flask import *
import pickle
import os
from pathlib import Path

from pystache import render

from main import *
from fullCalc import *
from checker import *

app = Flask(__name__)
load_dotenv()

if bool(os.environ.get('SERVER_INFO_CLEANER')) == True:
    dirTmpFiles = Path('./resultsBin')
    tmpFilesList = [i for i in os.walk('./resultsBin')][-1][-1]
    for i in tmpFilesList:
        os.remove(dirTmpFiles / Path(i))

host=os.environ.get("HOST")
user=os.environ.get("CLICKHOUSE_USERNAME")
password=os.environ.get("PASSWORD")

@app.route("/", methods=['GET', 'POST'])
def forecastServer():
    if request.method == 'POST':
        campaign=request.form.get('campaign')
        campaignId = request.form.get('campaignId')
        check = Checker(campaign)
        if check.campaignId is not None:
            if not check.checkId() and check.campaignName is None:
                return make_response(redirect(url_for('notFound', 
                                                      campaign=campaign)))
        if check.campaignName is not None:
            if not check.checkName() and check.campaignId is None:
                return make_response(redirect(url_for('notFound',
                                                      campaign=campaign)))
        if campaign is None and campaignId!='':
            campaign=getCampaignById(host=host, 
                                        user=user, 
                                        password=password, 
                                        campaignId=campaignId)
            print('CAMPAIGN: ' + campaignId)
        pred_n=int(request.form.get('pred_n'))
        minAccurancy=float(request.form.get('accurancy'))
        result = main(campaign, 
                        pred_n=pred_n, 
                        minAccurancy=minAccurancy)
        campaign=campaign.replace(' | ', '_')
        if len(result) == 1:
            res = make_response(redirect('/not_found'))
            res.set_cookie('campaign', campaign)
        else:
            res = make_response(render_template('result.html', 
                            accurancy=round(result[0],3),
                            mean=round(result[1], 3), 
                            std=round(result[2], 3),
                            median=round(result[3], 3), 
                            predictLength=str(int(pred_n/24)) + 'days',
                            alpha=round(result[5], 3), 
                            beta=round(result[6],3),
                            gamma=round(result[7],3), 
                            tableName=url_for('table', campaign=campaign),
                            backlink=url_for('forecastServer'),
                            plotName=url_for('plot', campaign=campaign),
                            campaign=campaign,
                            sumShows='{:,}'.format(round(result[8],3)).replace(',', ' ')))
            with open(f'./resultsBin/{campaign}.pickle', 'wb') as f:
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
            res.set_cookie('plotName', url_for('plot', campaign=campaign))
            res.set_cookie('tableName', url_for('table', campaign=campaign))
            res.set_cookie('campaign', campaign)
            if os.path.exists('./resultsBin/campaignList.pickle'):
                with open('./resultsBin/campaignList.pickle', 'rb') as f:
                    campaignDict = pickle.load(f)
                campaignDict.update({campaign: url_for('lastResult', campaign=campaign)})
                with open('./resultsBin/campaignList.pickle', 'wb') as f:
                    pickle.dump(campaignDict, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                campaignDict = {campaign: url_for('lastResult', campaign=campaign)}
                with open('./resultsBin/campaignList.pickle', 'wb') as f:
                    pickle.dump(campaignDict, f, protocol=pickle.HIGHEST_PROTOCOL)
        return res
    elif request.method == 'GET':
        if os.path.exists('./resultsBin/campaignList.pickle'):
            with open('./resultsBin/campaignList.pickle', 'rb') as f:
                campaignDict = pickle.load(f)
        else:
            campaignDict = {}
        if bool(os.environ.get('FULL_CALC_FIRST')):
            return make_response(redirect(url_for('fullCalculator')))
        else:
            return render_template('index.html', length=len(campaignDict), 
                                    links=campaignDict, valsFoot=url_for('fullCalculator'))



@app.route('/full_calculator', methods=['GET', 'POST'])
def fullCalculator():
    if request.method == 'POST':
        custom=request.form.get('custom')
        if not custom:
            campaignId=request.form.get('campaignId')
            campaignName=None
            try:
                int(campaignId)
            except ValueError:
                campaignName=request.form.get('campaignId')
                campaignId=None
            cpa=request.form.get('cpa')
            bid=cpa
            cr=0
            ctr=0
            approve=0
            epc=0
            ecpm=0
        else:    
            try:
                bid = float(request.form.get('bid'))
            except ValueError:
                return redirect(url_for('valNotFound', value='bid'))
            try:
                approve = float(request.form.get('approve'))
            except ValueError:
                return redirect(url_for('valNotFound', value='approve'))
            approveDim = request.form.get('approveDim')
            try:
                cr = float(request.form.get('cr'))
            except ValueError:
                return redirect(url_for('valNotFound', value='cr'))
            crDim = request.form.get('crDim')
            try: 
                ctr = float(request.form.get('ctr'))
            except ValueError:
                return redirect(url_for('valNotFound', value='ctr'))
            ctrDim = request.form.get('ctrDim')
            if approveDim == '%':
                approve = approve/100
            if crDim == '%':
                cr = cr/100
            if ctrDim == '%':
                ctr = ctr/100
            epc=bid*cr*approve
            ecpm=epc*ctr*1000
        pred_n = int(request.form.get('pred_n'))
        minAccurancy = float(request.form.get('accurancy'))
        resultDict = fullCalc(bid=bid, approve=approve, cr=cr, 
                                ctr=ctr, epc=epc, ecpm=ecpm, pred_n=pred_n,
                                minAccurancy=minAccurancy,
                                campaignId=campaignId,
                                campaignName=campaignName)
        print(resultDict)
        try:
            if resultDict['err'] == "No shows":
                return make_response(redirect('/not_found'))
        except KeyError:
            pass
        campaign=resultDict['campaign']
        campaign=campaign.replace(' | ', '_')
        if len(resultDict.values()) == 1:
            res = make_response(redirect('/not_found'))
            res.set_cookie('campaign', campaign)
        else:
            res = make_response(render_template('full_result.html', 
                            bid='{:,}'.format(round(resultDict['bid'], 3)).replace(',', ' '),
                            approve='{:,}'.format(round(resultDict['approve'], 3)).replace(',', ' '),
                            cr='{:,}'.format(round(resultDict['cr'],3)).replace(',', ' '),
                            ctr=round(resultDict['ctr'], 3),
                            epc=round(resultDict['epc'], 3),
                            ecpm=round(resultDict['ecpm'], 3),
                            accurancy=round(resultDict['accurancy'], 3),
                            mean='{:,}'.format(round(resultDict['mean'],3)).replace(',', ' '), 
                            std='{:,}'.format(round(resultDict['std'], 3)).replace(',', ' '),
                            median='{:,}'.format(round(resultDict['median'], 3)).replace(',', ' '), 
                            predictLength=int(resultDict['pred_n']/24),
                            alpha=round(resultDict['alpha'], 3), 
                            beta=round(resultDict['beta'],3),
                            gamma=round(resultDict['gamma'],3), 
                            tableName=url_for('fullTable', campaign=campaign),
                            backlink=url_for('forecastServer'),
                            plotNameShows=url_for('fullPlotShows', campaign=campaign),
                            plotNameClicks=url_for('fullPlotClicks', campaign=campaign),
                            plotNamePostbacks=url_for('fullPlotPostbacks', campaign=campaign),
                            campaign=campaign,
                            sumShows='{:,}'.format(int(resultDict['sumShows'])).replace(',', ' '),
                            sumClicks='{:,}'.format(int(resultDict['sumClicks'])).replace(',', ' '),
                            sumPostbacksUnconf='{:,}'.format(int(resultDict['sumPostbacksUnconf'])).replace(',', ' '),
                            sumPostbacksConf='{:,}'.format(int(resultDict['sumPostbacksConf'])).replace(',', ' '),))
            with open(f'./resultsBin/full_{campaign}.pickle', 'wb') as f:
                    pickle.dump(resultDict, f, protocol=pickle.HIGHEST_PROTOCOL)
            res.set_cookie('plotName', url_for('plot', campaign=campaign))
            res.set_cookie('tableName', url_for('table', campaign=campaign))
            res.set_cookie('campaign', campaign)
            if os.path.exists('./resultsBin/fullCalcListCam.pickle'):
                with open('./resultsBin/fullCalcListCam.pickle', 'rb') as f:
                    campaignDict = pickle.load(f)
                campaignDict.update({campaign: url_for('fullLastResult', campaigns=campaign)})
                with open('./resultsBin/fullCalcListCam.pickle', 'wb') as f:
                    pickle.dump(campaignDict, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                campaignDict = {campaign: url_for('fullLastResult', campaigns=campaign)}
                with open('./resultsBin/fullCalcListCam.pickle', 'wb') as f:
                    pickle.dump(campaignDict, f, protocol=pickle.HIGHEST_PROTOCOL)
        return res

    elif request.method == 'GET':
        if os.path.exists('./resultsBin/fullCalcListCam.pickle'):
            with open('./resultsBin/fullCalcListCam.pickle', 'rb') as f:
                fullCalcDict = pickle.load(f)
        else:
            fullCalcDict = {}
        return render_template('full_calculator.html', 
                                    length=len(fullCalcDict), 
                                    links=fullCalcDict)

@app.route('/results/<campaign>', methods=['GET'])
def lastResult(campaign):
    try:
        with open(f'./resultsBin/{campaign}.pickle', 'rb') as f:
            listArgs = pickle.load(f)
        res = make_response(render_template('result.html', 
                            accurancy=listArgs[0],
                            mean=listArgs[1], std=listArgs[2],
                            median=listArgs[3], 
                            predictLength=listArgs[4],
                            alpha=listArgs[5], 
                            beta=listArgs[6],
                            gamma=listArgs[7], 
                            tableName=url_for('table', campaign=campaign),
                            backlink=url_for('forecastServer'),
                            plotName=url_for('plot', campaign=campaign),
                            campaign=campaign,
                            sumShows=listArgs[8]))
        return res
    except EOFError:
        res = make_response(render_template('fake_result.html', 
                        campaign=campaign,
                        backlink=url_for('forecastServer')))
        return res

@app.route('/full_results/<campaigns>', methods=['GET'])
def fullLastResult(campaigns):
    try:
        with open(f'./resultsBin/full_{campaigns}.pickle', 'rb') as f:
            dictArgs = pickle.load(f)
        res = make_response(render_template('full_result.html', 
                            bid='{:,}'.format(round(dictArgs['bid'], 3)).replace(',', ' '),
                            approve='{:,}'.format(round(dictArgs['approve'], 3)).replace(',', ' '),
                            cr='{:,}'.format(round(dictArgs['cr'],3)).replace(',', ' '),
                            ctr=round(dictArgs['ctr'], 3),
                            epc=round(dictArgs['epc'], 3),
                            ecpm=round(dictArgs['ecpm'], 3),
                            accurancy=round(dictArgs['accurancy'], 3),
                            mean='{:,}'.format(round(dictArgs['mean'],3)).replace(',', ' '), 
                            std='{:,}'.format(round(dictArgs['std'], 3)).replace(',', ' '),
                            median='{:,}'.format(round(dictArgs['median'], 3)).replace(',', ' '), 
                            predictLength=int(dictArgs['pred_n']/24),
                            alpha=round(dictArgs['alpha'], 3), 
                            beta=round(dictArgs['beta'],3),
                            gamma=round(dictArgs['gamma'],3), 
                            tableName=url_for('fullTable', campaign=campaigns),
                            backlink=url_for('forecastServer'),
                            plotNameShows=url_for('fullPlotShows', campaign=campaigns),
                            plotNameClicks=url_for('fullPlotClicks', campaign=campaigns),
                            plotNamePostbacks=url_for('fullPlotPostbacks', campaign=campaigns),
                            campaign=campaigns,
                            sumShows='{:,}'.format(int(dictArgs['sumShows'])).replace(',', ' '),
                            sumClicks='{:,}'.format(int(dictArgs['sumClicks'])).replace(',', ' '),
                            sumPostbacksUnconf='{:,}'.format(int(dictArgs['sumPostbacksUnconf'])).replace(',', ' '),
                            sumPostbacksConf='{:,}'.format(int(dictArgs['sumPostbacksConf'])).replace(',', ' '),))
        return res
    except EOFError:
        res = make_response(render_template('fake_result.html', 
                        campaign=campaigns,
                        backlink=url_for('forecastServer')))
        return res
        
@app.route('/not_found/<campaign>', methods=['GET'])
def notFound(campaign):
    return render_template('false_result.html', 
                            campaign=campaign, 
                            backlink=url_for("fullCalculator"))

@app.route('/info', methods=['GET'])
def info():
    return render_template('info.html')

@app.route('/lastResult', methods=['GET'])
def listResult():
    if os.path.exists('./resultsBin/fullCalcListCam.pickle'):
        with open('./resultsBin/fullCalcListCam.pickle', 'rb') as f:
            fullCalcDict = pickle.load(f)
    else:
        fullCalcDict = {}
    return render_template('last_predict.html', 
                                length=len(fullCalcDict), 
                                links=fullCalcDict)

@app.route("/plot/<campaign>", methods=['GET'])
def plot(campaign):
    plotName = f'{campaign}.html'
    return render_template(f'plots/plot_{plotName}')

@app.route("/table/<campaign>", methods=['GET'])
def table(campaign):
    tableName = f'{campaign}.html'
    return render_template(f'tables/table_{tableName}')

@app.route("/full_plot_shows/<campaign>", methods=['GET'])
def fullPlotShows(campaign):
    plotName = f'{campaign}.html'
    return render_template(f'plots/fullPlot_shows_{plotName}')

@app.route("/full_plot_clicks/<campaign>", methods=['GET'])
def fullPlotClicks(campaign):
    plotName = f'{campaign}.html'
    return render_template(f'plots/fullPlot_clicks_{plotName}')

@app.route("/full_plot_postbacks/<campaign>", methods=['GET'])
def fullPlotPostbacks(campaign):
    plotName = f'{campaign}.html'
    return render_template(f'plots/fullPlot_postbacks_{plotName}')

@app.route("/full_table/<campaign>", methods=['GET'])
def fullTable(campaign):
    tableName = f'{campaign}.html'
    return render_template(f'tables/fullTable_{tableName}')

@app.route("/value_<value>_not_found", methods=['GET'])
def valNotFound(value):
    return render_template('value_not_found.html', 
                            value=value, 
                            backlink1=url_for('forecastServer'),
                            backlink2=url_for('fullCalculator'))
