# Script Runner
Authors: Chris Armstrong, Bereket Abraham

##### What it solves:
- Today there are a bunch of ipython notebooks hidden away on people's dev boxes
- While notebooks are pretty convenient when compared to the terminal, there is still a bit of a learning curve, especially for those with no programming background (most of the org!)
- Wouldn't it be great if we could "appify" all of these scripts and notebooks to make them even simpler for everyone in the org to use? That's what Script runner does!
 
##### What it does:
- Takes your ipython notebook and a config (soon to be handled via self serve UI) and transforms the notebook into a shiny and easy to use web app
- The UI is semi-customizable via the config parameters you provide
- Pipes any notebook output into the web app. Dataframe tables are auto formatted to be filterable and downloadable!
 
##### Current limitations:
- No self serve config submission. For now, please send me your notebooks with the first cell housing the config (more on this below)
- Doesn't support matplot's at the moment. I know it's possible, so this should be coming very soon.
- Only the following data types for parameters that are supported: string, integer, boolean. List and dictionary support coming soon.
 
### Instructions:
 
##### How to run an app:
- Simply follow the link above, select one of the notebooks and then fill out the required fields and hit submit.
- For install instructions please refer to `setup.md`.
 
##### How to submit a notebook to be appified:
- First, ensure your notebooks runs without any errors!
- Also note that any output your notebook generates will be shown to the end user. Clean up any unwanted outputs!
- If you want to output a dataframe, use `print df.to_html(index=False)`
- Remove the parameters from the notebook (these will be set by Script Runner when the user enters them)
- Add the config cell (needs to be the first cell of the notebook)
 
### Config structure:
```json
{
    "nb_display_name": "Example Metric",
    "nb_description": "Shows the example metric over time for the past month",
    "nb_filename": "example.ipynb",
    "params":[
        {
            "name":"user_id",
            "display_name":"User ID",
            "description":"",
            "input_type":"integer"
        },
        {
            "name":"username",
            "display_name":"Username",
            "description":"",
            "input_type":"string"
        }
    ]
}
```

