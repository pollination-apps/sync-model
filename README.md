# Sync Model

Sync Pollination Hbjson Model AECTech 2022

## Quickstart

Install dependencies:

```
> pip install -r requirements.txt
```

Start Streamlit

```
> streamlit run app.py

  You can now view your Streamlit app in your browser.

  Network URL: http://172.17.0.2:8501
  External URL: http://152.37.119.122:8501

```

Make changes to your app in the `app.py` file inside the "app" folder.

## Run inside Docker image locally (Optional)

You can run the app locally inside Docker to ensure the app will work fine after the deployment.

You need to install Docker on your machine in order to be able to run this command

```
> pollination-apps run app ladybug-tools --name "Sync Model"
```

## Deploy to Pollination

```
> pollination-apps deploy app --name "Sync Model" --public --api-token "Your api token from Pollination"
```




