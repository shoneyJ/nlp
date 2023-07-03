import torch.nn as nn
import torch
import random
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from VectorizeClass import Vectorize
import time
import math

from NN import RNN

class Train():
    def __init__(self,df_en,doLoad=False,testing=False):
        self.df_en=df_en     
        self.vectorizer = Vectorize(1,1)
        self.vectorizer.fit(doc=df_en["name"])
       
        self.inputSize=self.vectorizer.getVocabLen()
        self.n_hidden = 256*4
        
        self.df_category = self.df_en.groupby('category')       
        self.all_category = list(self.df_category.groups.keys()) 
        if testing:
            self.all_category=random.choices(self.all_category,k=20)

        self.n_category = len(self.all_category)
        self.rnn= torch.load('ngram-rnn-classification.pt') if doLoad else  RNN(self.inputSize, self.n_hidden, self.n_category)
        self.learning_rate=0.005
        self.criterion = nn.NLLLoss()

        self.current_loss = 0
        self.all_losses = []
 

    def train(self,category_tensor, name_tensor):
    
        hidden = self.rnn.initHidden()

        self.rnn.zero_grad()

        for i in range(name_tensor.size()[0]):     

            output, hidden = self.rnn(name_tensor[i], hidden)

        loss = self.criterion(output, category_tensor)
        loss.backward()

        # for p in self.rnn.parameters():
        #     p.data.add_(-self.learning_rate, p.grad.data)

            # Add parameters' gradients to their values, multiplied by learning rate
        for p in self.rnn.parameters():
            p.data.add_(p.grad.data, alpha=-self.learning_rate)



        return output, loss.item()

    
    def randomTrainingExample(self):
     
        randcategory = random.choice(self.all_category)
        # get feature name from the category
        random_feature_indices = self.df_category.indices[randcategory]
        
        index = random_feature_indices[random.randint(0, len(random_feature_indices) - 1)]

        # ngramNameArray = self.vectorizer.getTransformedVectorByIndex(index)

        name =self.df_en.iloc[index]["name"]
        
        category_tensor = torch.tensor([self.all_category.index(randcategory)], dtype=torch.long)
        # ngramOnceArray = np.where(ngramNameArray==1)[0]

        # name_tensor=torch.zeros(len(ngramOnceArray),1, self.inputSize)
       
        # for i in range(ngramOnceArray.size):
           
        #     name_tensor[i][0][ngramOnceArray[i]] = 1

        name_tensor = self.nameToTensor(name)           
        
        
        return randcategory, name, category_tensor, name_tensor
    
    
    def categoryFromOutput(self,output):
        
        _, top_i = output.topk(1)
        
        cat_i = top_i[0].item()
        
        return self.all_category[cat_i], cat_i
    

    def run(self,n_iters):
        start = time.time()
        for epoch in range(1, n_iters + 1):
    
            category, name, category_tensor, name_tensor = self.randomTrainingExample()
            
            output, loss = self.train(category_tensor, name_tensor)
            self.current_loss += loss
             # Print ``iter`` number, loss, name and guess

            if epoch % 10000 == 0:
                guess, guess_i = self.categoryFromOutput(output)
                correct = '✓' if guess == category else '✗ (%s)' % category
                
                print('%d %d%% (%s) %.4f %s / %s %s' % (epoch, 
                                                epoch / n_iters * 100,
                                                self.timeSince(start),
                                                loss,
                                                name, 
                                                guess, 
                                                correct))

            if epoch % 5000 == 0:
                self.all_losses.append(self.current_loss / 5000)
                self.current_loss = 0
            
        self.plot()
        torch.save(self.rnn,'ngram-rnn-classification.pt')
    

    def plot(self):
        plt.figure()
        plt.plot(self.all_losses)
        plt.savefig('histogram.png', dpi=400)
    

         # Just return an output given a numpy  array
    def evaluate(self,tensor):
        hidden = self.rnn.initHidden()

        for i in range(tensor.size()[0]):
            output, hidden = self.rnn(tensor[i], hidden)

        return output
    
    def timeSince(self,since):
        now = time.time()
        s = now - since
        m = math.floor(s / 60)
        s -= m * 60
        return '%dm %ds' % (m, s)
    
    def nameToTensor(self,name):
        # create empty tensor with 
        vectorized=self.vectorizer.transform(list(name.split()))
        n_vectors=len(vectorized.indices)

        name_tensor=torch.zeros(n_vectors,1, self.inputSize)
        for i in range(n_vectors):
           
            name_tensor[i][0][vectorized.indices[i]] = 1
        
        return name_tensor


    def predict(self,name, n_predictions=3):
        print('\n> %s' % name)
        with torch.no_grad():
            output = self.evaluate(self.nameToTensor(name))

            # Get top N categories
            topv, topi = output.topk(n_predictions, 1, True)
            predictions = []

            for i in range(n_predictions):
                value = topv[0][i].item()
                category_index = topi[0][i].item()
                print('(%.2f) %s' % (value, self.all_category[category_index]))
                predictions.append([value, self.all_category[category_index]])
    
    def confusionMatix(self):
        # Keep track of correct guesses in a confusion matrix

        n_categories = len(self.all_category)
        confusion = torch.zeros(n_categories, n_categories)
        n_confusion = 10000

        # Go through a bunch of examples and record which are correctly guessed
        for i in range(n_confusion):
            category, name, category_tensor, name_tensor = self.randomTrainingExample()
            output = self.evaluate(name_tensor)
            guess, guess_i = self.categoryFromOutput(output)
            category_i =self.all_category.index(category)
            confusion[category_i][guess_i] += 1
        
        # Normalize by dividing every row by its sum
        for i in range(n_categories):
            confusion[i] = confusion[i] / confusion[i].sum()
        
        # Set up plot
        fig = plt.figure()
        ax = fig.add_subplot(111)
        cax = ax.matshow(confusion.numpy())
        fig.colorbar(cax)

        # Set up axes
        ax.set_xticklabels([''] + self.all_category, rotation=45)
        ax.set_yticklabels([''] + self.all_category)

        # Force label at every tick
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(1))

        # sphinx_gallery_thumbnail_number = 2
        plt.show()
        plt.savefig('confusion.png', dpi=400)
        

    

   
    
   

