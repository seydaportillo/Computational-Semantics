# -*- coding: utf-8 -*-
"""SON adlı not defterinin kopyası

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16Dsby8H1SHyHw1QU7kEs2MfTBsINKc-l
"""

# INSTALL MISSING PACKAGES
from importlib.util import find_spec
import pip

required_packages = ['torch', 'datasets', 'pandas']

for package in required_packages:
  if find_spec(package) is None:
    print(f'Installing package: {package}...')
    pip.main(['install', package])

!pip uninstall transformers
!pip uninstall adapter-transformers
!pip install -U adapter-transformers


# IMPORT PACKAGES
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pandas import DataFrame
import numpy as np
from scipy.spatial.distance import cosine
import matplotlib.pyplot as plt
import torch
from torch.utils.data import Dataset, DataLoader
!pip install datasets
from datasets import Dataset, DatasetDict

import transformers
from transformers import BertTokenizer, BertModel
from transformers import pipeline
from transformers import AutoConfig, AutoTokenizer, AutoModelWithHeads, AutoModelForSequenceClassification
from transformers import TrainingArguments, AdapterTrainer, EvalPrediction

from transformers import TextClassificationPipeline
from transformers import TrainerCallback

!pip install prettytable
from prettytable import PrettyTable

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased',
                                  output_hidden_states = True,
                                  )
import random

# Set the random seed for Python's random module
random_seed = 42
random.seed(random_seed)

# Set the random seed for NumPy
np.random.seed(random_seed)

# Set the random seed for PyTorch
torch.manual_seed(random_seed)
torch.cuda.manual_seed(random_seed)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

"""## 1. Load data"""

# Load the dataset
file_path = '/content/twitter_training - twitter_training.csv.csv'
df = pd.read_csv(file_path)

# Handle missing values in the 'Sentence' column
df['Sentences'] = df['Sentences'].fillna('')  # Replace NaN with an empty string

# Assuming 'Sentiment' is the target variable and 'Sentences' is the feature
X = df['Sentences']
y = df['Sentiment']

# Display the first few rows of the DataFrame
print(df.head())

# Assuming 'Sentiment' is the target variable and 'Sentences' is the feature
# Split the data into three sets: 70 Training + 10 Validation + 20 Test

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_test, X_val, y_test, y_val = train_test_split(X_temp, y_temp, test_size=0.33, random_state=42)

# Calculate percentages
total_samples = len(X)
percentage_train = len(X_train) / total_samples * 100
percentage_val = len(X_val) / total_samples * 100
percentage_test = len(X_test) / total_samples * 100

# Display the percentages to make it sure
print(f"Percentage of Training Set: {percentage_train:.2f}%")
print(f"Percentage of Validation Set: {percentage_val:.2f}%")
print(f"Percentage of Test Set: {percentage_test:.2f}%")

# Check whether the dataset is balanced
sns.countplot(x='Sentiment', data=df)
plt.title('Class Distribution')
plt.show()

# Map 'Positive' to 1 and 'Negative' to 0 'Neutral' to 2 'Irrelevant' to 3
df_train = pd.DataFrame({'Sentences': X_train, 'sentiment': y_train})
df_val = pd.DataFrame({'Sentences': X_val, 'sentiment': y_val})
df_test = pd.DataFrame({'Sentences': X_test, 'sentiment': y_test})

df_train['label'] = df_train['sentiment'].map({'Positive': 1, 'Negative': 0, 'Neutral': 2, 'Irrelevant':3})
df_val['label'] = df_val['sentiment'].map({'Positive': 1, 'Negative': 0, 'Neutral': 2, 'Irrelevant':3})
df_test['label'] = df_test['sentiment'].map({'Positive': 1, 'Negative': 0, 'Neutral': 2, 'Irrelevant':3})

# Convert the pandas DataFrames to Hugging Face Dataset objects
train_dataset = Dataset.from_pandas(df_train)
validation_dataset = Dataset.from_pandas(df_val)
test_dataset = Dataset.from_pandas(df_test)

# Create a DatasetDict
dataset = DatasetDict({
    'train': train_dataset,
    'validation': validation_dataset,
    'test': test_dataset
})

#TRAINING AN ADAPTER

# This function organizes the data as required by the model
def encode_batch(batch):
  """Encodes a batch of input data using the model tokenizer."""
  return tokenizer(batch["Sentences"], max_length=80, truncation=True, padding="max_length")

# Encode the input data
dataset = dataset.map(encode_batch, batched=True)

# The transformers model expects the target class column to be named "labels"
dataset = dataset.rename_column("label", "labels")

# Transform to pytorch tensors and only output the required columns
dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

#DEFINE THE FEAUTURES OF THE MODEL

# Load the BERT configuration with custom settings
config = AutoConfig.from_pretrained(
    "bert-base-uncased",  # Specifies the pre-trained model, in this case, BERT base uncased (110M parameters)
    num_labels=4,  # Number of labels for classification (4 in this case, representing multi-class sentiment classification)
    id2label={0: "👎", 1: "👍", 2: "😐", 3: "🚫"}  # Mapping from label indices to human-readable labels
)

# Load the pre-trained BERT model for sequence classification with the above configuration
model = AutoModelForSequenceClassification.from_pretrained(
    "bert-base-uncased",  # Specifies the pre-trained model to use
    config=config  # The configuration object defining model parameters
)

# Load the tokenizer for the 'bert-base-uncased' model
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Adding an adapter to the model
model.add_adapter("sentiment")  # Adds an adapter with the name 'sentiment'

# This step configures the model to update only the adapter parameters during training.
model.train_adapter(["sentiment"])  # Specifies that only the 'sentiment' adapter should be trained

# This step tells the model to use the specified adapter(s) during inference and/or training.
model.set_active_adapters(["sentiment"])  # Activates the 'sentiment' adapter

#DEFINE PARAMETERS FOR THE TRAINING

# Define the training arguments
training_args = TrainingArguments(
    learning_rate=1e-05,
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    logging_steps=100,
    output_dir="./training_output",
    overwrite_output_dir=True,
    remove_unused_columns=False,
)

# Define the loss logging callback
class LossLoggingCallback(TrainerCallback):
    def __init__(self):
        self.losses = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        print(f"Logging at step {state.global_step}: {logs}")
        if 'loss' in logs:
            self.losses.append(logs['loss'])

# Initialize the callback
loss_logging_callback = LossLoggingCallback()

# Function to compute accuracy
def compute_accuracy(p: EvalPrediction):
    preds = np.argmax(p.predictions, axis=1)
    accuracy = (preds == p.label_ids).mean()
    print(f"Accuracy: {accuracy}")
    return {"eval_acc": accuracy}

#Adapter trainer
trainer = AdapterTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    compute_metrics=compute_accuracy,
    callbacks=[loss_logging_callback]
)

# TRAIN the model
trainer.train()

#CHECK THE LOSS

plt.bar(range(len(loss_logging_callback.losses)), loss_logging_callback.losses)
plt.xlabel('Steps')
plt.ylabel('Loss')
plt.title('Loss per Logging Step')
plt.show()

#EVALUATION AND ERROR ANALYSIS
trainer.evaluate() # on the validation set! As stated above where we define our trainer

# Creating a text classification pipeline, using our model (with the trained adapter added)
classifier = TextClassificationPipeline(model=model, # The model to use for classification
                                        tokenizer=tokenizer, # The tokenizer to process the input text
                                        device=training_args.device.index # The device (CPU/GPU) to run the model on
                                        )

# @title Model prediction
classifier("The biggest disappointment of my life came a year ago.")[0]['label'] # Use the classifier to predict the label of the given text

# @title How confident is our model with its prediction:
classifier("The biggest disappointment of my life came a year ago.")[0]['score']

#Evaluate the model on the test set and inspect the model's errors.
trainer.evaluate(eval_dataset=dataset['test'])

# Initialize counts for incorrect predictions
incorrect_counts = {'Negative': 0, 'Positive': 0, 'Neutral': 0, 'Irrelevant': 0}

for sentence, label in list(zip(df_test['Sentences'], df_test['sentiment']))[:100]:
    prediction = classifier(sentence)
    predicted_label = prediction[0]['label']

    # Check if the predicted label does not match the actual label
    if (
        (label == 'Negative' and predicted_label != '👎') or
        (label == 'Positive' and predicted_label != '👍') or
        (label == 'Neutral' and predicted_label != '😐') or
        (label == 'Irrelevant' and predicted_label != '🚫')
    ):
        # Increment count for the respective label
        incorrect_counts[label] += 1

# Create a PrettyTable
contingency_table = PrettyTable()
contingency_table.field_names = ["Sentiment", "Incorrect Predictions Count"]

# Populate the PrettyTable
for label, count in incorrect_counts.items():
    contingency_table.add_row([label, count])

# Print the PrettyTable
print("Contingency Table:")
print(contingency_table)

# Get the total number of incorrect predictions
print(f"Sum of Incorrect Predictions Count: {total_incorrect_predictions}")
# Get the total number of tweets in our Data Frame
num_sentences = len(df['Sentences'])
print(f"Number of Sentences: {num_sentences}")

# Assign the number of mistakes made by the model
num_mistakes = sum(incorrect_counts.values())

# Assuming total_examples is the total number of examples
total_examples = len(df['Sentences'])

# Calculate the success percentage
success_percentage = (1 - num_mistakes / total_examples) * 100

print(f"Correct Prediction Percentage: {success_percentage:.2f}%")

# Print examples for each label
for label, examples in incorrect_examples.items():
    print(f"Examples for {label}:")
    for example in examples:
        print(f"    Sentence: {example[0]}, Predicted Label: {example[1]}")
    print()
