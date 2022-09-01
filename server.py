# Public libs
import os.path
from flask import *
import pickle
import warnings
from clickhouse_driver.errors import SocketTimeoutError
# Personal libs
from model.fullCalc import *
from services.cleaner import envCleaner
from services.loger import Loger

warnings.simplefilter(action='ignore', category=FutureWarning)

app = Flask(__name__)
load_dotenv()

# TODO Delete all print() methods


# Set extra env variables
os.environ.setdefault('PROJECT_PATH', os.path.dirname(__file__))

# Clean temp files
if bool(os.environ.get('SERVER_INFO_CLEAN')):
    envCleaner('bin')

if bool(os.environ.get('SERVER_PLOT_CLEAN')):
    envCleaner('plot')

if bool(os.environ.get('SERVER_TABLE_CLEAN')):
    envCleaner('table')

# Init ClickHouse driver variable
host = os.environ.get("HOST")
user = os.environ.get("CLICKHOUSE_USERNAME")
password = os.environ.get("PASSWORD")
#Init Loger class
loger = Loger()


@app.route('/', methods=['GET', 'POST'])
def fullCalculator():
    if request.method == 'POST':
        if len(request.form)>0:
            argsInUrl=False
        elif len(request.args)>0:
            argsInUrl=True

        if not argsInUrl:
            campaignId = request.form.get('campaignId')
        else:
            campaignId = request.args.get('campaignId')
        campaignName = None
        try:
            int(campaignId)
        except ValueError:
            if not argsInUrl:
                campaignName = request.form.get('campaignId')
            else:
                campaignName = request.args.get('campaignId')
            campaignId = None
        if not argsInUrl:
            cpa = request.form.get('cpa')
            customApprove = request.form.get('approve')
        else:
            cpa = request.args.get('cpa')
            customApprove = request.args.get('approve')
        if cpa != '':
            try:
                bid = int(cpa)
            except ValueError:
                return make_response(
                    redirect(url_for("valNotFound",
                                     value="CPA")))
        else:
            bid = None

        if customApprove != '':
            try:
                approve = int(customApprove)
            except ValueError:
                return make_response(
                    redirect(url_for("valNotFound",
                                     value="approve")))
        else:
            approve = None
        if not argsInUrl:
            pred_n = int(request.form.get('pred_n'))
            minAccurancy = float(request.form.get('accurancy'))
        else:
            pred_n = int(request.args.get('pred_n'))
            minAccurancy = float(request.args.get('accurancy'))
        
        resultDict = fullCalc(pred_n=pred_n,
                              minAccurancy=minAccurancy,
                              campaignId=campaignId,
                              campaignName=campaignName,
                              custom_approve=approve,
                              custom_bid=bid)

        try:
            if resultDict['err'] == "No shows":
                return make_response(
                    redirect(url_for("valNotFound",
                                     value="campaign name/id")))
        except KeyError:
            pass

        meanClicks = resultDict['meanClicks']
        stdClicks = resultDict['stdClicks']
        medianClicks = resultDict['medianClicks']
        meanPostbacks = resultDict['meanPostbacks']
        stdPostbacks = resultDict['stdPostbacks']
        medianPostbacks = resultDict['medianPostbacks']
        meanConfirmPostbacks = resultDict['meanConfirmPostbacks']
        stdConfirmPostbacks = resultDict['stdConfirmPostbacks']
        medianConfirmPostbacks = resultDict['medianConfirmPostbacks']

        campaign = resultDict['campaign']
        campaign = campaign.replace(' | ', '_')
        if len(resultDict.values()) == 1:
            res = make_response(redirect('/not_found'))
            res.set_cookie('campaign', campaign)
        else:
            diffShowsForecastUnform = -int(resultDict['median']) + int(int(resultDict['sumShows']) /
                                                                       int(resultDict['pred_n'] / 24))
            if diffShowsForecastUnform >= 0:
                diffShowsCell = 'darkgreen'
                arrPathShows = url_for('static', filename='img/arrowUp.svg')
            else:
                diffShowsCell = 'darkred'
                arrPathShows = url_for('static', filename='img/arrowDown.svg')

            diffClicksForecastUnform = -int(resultDict['medianClicks']) + \
                                       int(int(resultDict['sumClicks']) /
                                           int(resultDict['pred_n'] / 24))
            if diffClicksForecastUnform >= 0:
                diffClicksCell = 'darkgreen'
                arrPathClicks = url_for('static', filename='img/arrowUp.svg')
            else:
                diffClicksCell = 'darkred'
                arrPathClicks = url_for('static', filename='img/arrowDown.svg')

            diffPostForecastUnform = -int(resultDict['medianPostbacks']) + \
                                     int(int(resultDict['sumPostbacksUnconf']) /
                                         int(resultDict['pred_n'] / 24))
            if diffPostForecastUnform >= 0:
                diffPostCell = 'darkgreen'
                arrPathPost = url_for('static', filename='img/arrowUp.svg')
            else:
                diffPostCell = 'darkred'
                arrPathPost = url_for('static', filename='img/arrowDown.svg')

            diffConfPostForecastUnform = -int(resultDict['medianConfirmPostbacks']) + \
                                         int(int(resultDict['sumPostbacksConf']) /
                                             int(resultDict['pred_n'] / 24))
            if diffConfPostForecastUnform >= 0:
                diffConfPostCell = 'darkgreen'
                arrPathConfPost = url_for('static', filename='img/arrowUp.svg')
            else:
                diffConfPostCell = 'darkred'
                arrPathConfPost = url_for('static', filename='img/arrowDown.svg')

            if not argsInUrl:
                res = make_response(render_template('full_result.html',
                                                bid='{:,}'.format(round(resultDict['bid'], 3)).replace(',', ' '),
                                                userBid=cpa,
                                                approve='{:,}'.format(round(resultDict['approve'], 3)).replace(',',
                                                                                                               ' '),
                                                userApprove=customApprove,
                                                cr='{:,}'.format(round(resultDict['cr'], 3)).replace(',', ' '),
                                                ctr=round(resultDict['ctr'], 3),
                                                epc=round(resultDict['epc'], 3),
                                                ecpm=round(resultDict['ecpm'], 3),
                                                accurancy=round(resultDict['accurancy'], 3),
                                                mean='{:,}'.format(int(resultDict['mean'])).replace(',', ' '),
                                                std='{:,}'.format(int(resultDict['std'])).replace(',', ' '),
                                                median='{:,}'.format(int(resultDict['median'])).replace(',', ' '),
                                                meanClicks='{:,}'.format(int(meanClicks)).replace(',', ' '),
                                                stdClicks='{:,}'.format(int(stdClicks)).replace(',', ' '),
                                                medianClicks='{:,}'.format(int(medianClicks)).replace(',', ' '),
                                                meanPost='{:,}'.format(int(meanPostbacks)).replace(',', ' '),
                                                stdPost='{:,}'.format(int(stdPostbacks)).replace(',', ' '),
                                                medianPost='{:,}'.format(int(medianPostbacks)).replace(',', ' '),
                                                meanConfirmPostbacks='{:,}'.format(int(meanConfirmPostbacks)).replace(
                                                    ',', ' '),
                                                stdConfirmPostbacks='{:,}'.format(int(stdConfirmPostbacks)).replace(',',
                                                                                                                    ' '),
                                                medianConfirmPostbacks='{:,}'.format(
                                                    int(medianConfirmPostbacks)).replace(',', ' '),
                                                predictLength=int(resultDict['pred_n'] / 24),
                                                alpha=round(resultDict['alpha'], 3),
                                                beta=round(resultDict['beta'], 3),
                                                gamma=round(resultDict['gamma'], 3),
                                                tableName=url_for('fullTable', campaign=campaign),
                                                backlink=url_for('fullCalculator'),
                                                plotNameShows=url_for('fullPlot', campaign=campaign),
                                                factorAnalysis=url_for('factorAnalysis', campaign=campaign),
                                                campaign=campaign,
                                                sumShows='{:,}'.format(int(resultDict['sumShows'])).replace(',', ' '),
                                                sumClicks='{:,}'.format(int(resultDict['sumClicks'])).replace(',', ' '),
                                                sumPostbacksUnconf='{:,}'.format(
                                                    int(resultDict['sumPostbacksUnconf'])).replace(',', ' '),
                                                sumPostbacksConf='{:,}'.format(
                                                    int(resultDict['sumPostbacksConf'])).replace(',', ' '),
                                                dailySumShows='{:,}'.format(int(int(resultDict['sumShows']) / int(
                                                    resultDict['pred_n'] / 24))).replace(',', ' '),
                                                dailySumClicks='{:,}'.format(int(int(resultDict['sumClicks']) / int(
                                                    resultDict['pred_n'] / 24))).replace(',', ' '),
                                                dailySumPost='{:,}'.format(
                                                    int(int(resultDict['sumPostbacksUnconf']) / int(
                                                        resultDict['pred_n'] / 24))).replace(',', ' '),
                                                dailySumConfPost='{:,}'.format(
                                                    int(int(resultDict['sumPostbacksConf']) / int(
                                                        resultDict['pred_n'] / 24))).replace(',', ' '),
                                                diffShowsCell=diffShowsCell,
                                                diffShowsForecast='{:,}'.format(diffShowsForecastUnform).replace(',',
                                                                                                                 ' '),
                                                diffClicksCell=diffClicksCell,
                                                diffClicksForecast='{:,}'.format(diffClicksForecastUnform).replace(',',
                                                                                                                   ' '),
                                                diffPostCell=diffPostCell,
                                                diffPostForecast='{:,}'.format(diffPostForecastUnform).replace(',',
                                                                                                               ' '),
                                                diffConfPostCell=diffConfPostCell,
                                                diffConfPostForecast='{:,}'.format(diffConfPostForecastUnform).replace(
                                                    ',', ' '),
                                                arrPathShows=arrPathShows, arrPathClicks=arrPathClicks,
                                                arrPathPost=arrPathPost, arrPathConfPost=arrPathConfPost))
            else:
                request.accept_charsets
                request.accept_encodings
                res=make_response(jsonify({
                            'input_data': {
                                'campaign': resultDict['campaign'], 
                                'bid': resultDict['bid'],
                                'userBid': cpa,
                                'approve': resultDict['approve'],
                                'userApprove': customApprove,
                                'cr': resultDict['cr'], 
                                'ctr': resultDict['ctr'],
                                'epc': resultDict['epc'],
                                'ecpm': resultDict['ecpm']
                            },
                            'model_data':{
                                'accurancy': resultDict['accurancy'],
                                'mean': resultDict['mean'],
                                'std': resultDict['std'],
                                'median': resultDict['median']
                            },
                            'approve_check': {
                                'postbacks_forecast': int(int(resultDict['sumPostbacksUnconf']) / int(
                                                        resultDict['pred_n'] / 24)),
                                'conf_postbacks_forecast': int(int(resultDict['sumPostbacksConf']) / int(
                                                        resultDict['pred_n'] / 24))
                            },
                            'pathes': {
                                'tableName': url_for('fullTable', campaign=campaign),
                                'plotNameShows': url_for('fullPlot', campaign=campaign),
                                'factorAnalysis': url_for('factorAnalysis', campaign=campaign)
                            },
                            'trend': {
                                'shows': diffShowsForecastUnform,
                                'clicks': diffClicksForecastUnform,
                                'postbacks':diffPostForecastUnform,
                                'confirmed_postbacks': diffConfPostForecastUnform
                            }
                }))

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
        print(request.accept_charsets)
        print(request.accept_encodings)
        print(request.accept_languages)
        print(request.accept_mimetypes)
        print(request.access_route)
        print(request.args)
        print(request.authorization)
        print(request.base_url)
        print(request.blueprint)
        print(request.cache_control)
        print(request.cookies)
        print(request.data)
        print(request.content_length)
        print(request.content_md5)
        print(request.content_encoding)
        print(request.endpoint)
        print(request.files)
        print(request.environ)
        print(request.date)
        print(request.form)
        if os.path.exists('./resultsBin/fullCalcListCam.pickle'):
            with open('./resultsBin/fullCalcListCam.pickle', 'rb') as f:
                fullCalcDict = pickle.load(f)
        else:
            fullCalcDict = {}
        return render_template('full_calculator.html',
                               length=len(fullCalcDict),
                               links=fullCalcDict)


@app.route('/full_results/<campaigns>', methods=['GET'])
def fullLastResult(campaigns):
    loger.requestMessage(req=request)
    try:
        with open(f'./resultsBin/full_{campaigns}.pickle', 'rb') as f:
            dictArgs = pickle.load(f)
        res = make_response(render_template('full_result.html',
                                            bid='{:,}'.format(round(dictArgs['bid'], 3)).replace(',', ' '),
                                            approve='{:,}'.format(round(dictArgs['approve'], 3)).replace(',', ' '),
                                            cr='{:,}'.format(round(dictArgs['cr'], 3)).replace(',', ' '),
                                            ctr=round(dictArgs['ctr'], 3),
                                            epc=round(dictArgs['epc'], 3),
                                            ecpm=round(dictArgs['ecpm'], 3),
                                            accurancy=round(dictArgs['accurancy'], 3),
                                            mean='{:,}'.format(round(dictArgs['mean'], 3)).replace(',', ' '),
                                            std='{:,}'.format(round(dictArgs['std'], 3)).replace(',', ' '),
                                            median='{:,}'.format(round(dictArgs['median'], 3)).replace(',', ' '),
                                            predictLength=int(dictArgs['pred_n'] / 24),
                                            alpha=round(dictArgs['alpha'], 3),
                                            beta=round(dictArgs['beta'], 3),
                                            gamma=round(dictArgs['gamma'], 3),
                                            tableName=url_for('fullTable', campaign=campaigns),
                                            backlink=url_for('fullCalculator'),
                                            plotNameShows=url_for('fullPlot', campaign=campaigns),
                                            factorAnalysis=url_for('factorAnalysis', campaign=campaigns),
                                            campaign=campaigns,
                                            sumShows='{:,}'.format(int(dictArgs['sumShows'])).replace(',', ' '),
                                            sumClicks='{:,}'.format(int(dictArgs['sumClicks'])).replace(',', ' '),
                                            sumPostbacksUnconf='{:,}'.format(
                                                int(dictArgs['sumPostbacksUnconf'])).replace(',', ' '),
                                            sumPostbacksConf='{:,}'.format(int(dictArgs['sumPostbacksConf'])).replace(
                                                ',', ' '),
                                            dailySumShows='{:,}'.format(
                                                int(int(dictArgs['sumShows']) / int(dictArgs['pred_n'] / 24))).replace(
                                                ',', ' '),
                                            dailySumClicks='{:,}'.format(
                                                int(int(dictArgs['sumClicks']) / int(dictArgs['pred_n'] / 24))).replace(
                                                ',', ' '),
                                            dailySumPost='{:,}'.format(
                                                int(int(dictArgs['sumShows']) / int(dictArgs['pred_n'] / 24))).replace(
                                                ',', ' '),
                                            dailySumConfPost='{:,}'.format(
                                                int(int(dictArgs['sumShows']) / int(dictArgs['pred_n'] / 24))).replace(
                                                ',', ' ')))
        return res
    except EOFError:
        res = make_response(render_template('fake_result.html',
                                            campaign=campaigns,
                                            backlink=url_for('fullCalculator')))
        return res


@app.route('/not_found/<campaign>', methods=['GET'])
def notFound(campaign):
    loger.requestMessage(req=request)
    return render_template('false_result.html',
                           campaign=campaign,
                           backlink=url_for("fullCalculator"))


@app.route('/info', methods=['GET'])
def info():
    loger.requestMessage(req=request)
    return render_template('info.html')


@app.route('/lastResult', methods=['GET'])
def listResult():
    loger.requestMessage(req=request)
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
    loger.requestMessage(req=request)
    plotName = f'{campaign}.html'
    return render_template(f'plots/plot_{plotName}')


@app.route("/table/<campaign>", methods=['GET'])
def table(campaign):
    loger.requestMessage(req=request)
    tableName = f'{campaign}.html'
    return render_template(f'tables/table_{tableName}')


@app.route("/full_plot_shows/<campaign>", methods=['GET'])
def fullPlot(campaign):
    loger.requestMessage(req=request)
    plotName = f'{campaign}.html'
    return render_template(f'plots/fullPlot_shows_{plotName}')


@app.route("/factor_analysis/<campaign>", methods=['GET'])
def factorAnalysis(campaign):
    loger.requestMessage(req=request)
    camName = f'{campaign}.html'
    return render_template(f'factorAnalysis/factor_{camName}')


@app.route("/full_table/<campaign>", methods=['GET'])
def fullTable(campaign):
    loger.requestMessage(req=request)
    tableName = f'{campaign}.html'
    return render_template(f'tables/fullTable_{tableName}')


@app.route("/value_<value>_not_found", methods=['GET'])
def valNotFound(value):
    loger.requestMessage(req=request)
    return render_template('value_not_found.html',
                           value=value,
                           backlink=url_for('fullCalculator'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
