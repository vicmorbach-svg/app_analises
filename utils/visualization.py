import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

def set_style():
    """Define o estilo visual para os gráficos."""
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except:
        try:
            plt.style.use('seaborn-whitegrid')
        except:
            plt.style.use('default')

    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'


def plot_bar_chart(data, x, y, title, xlabel=None, ylabel=None,
                  color='skyblue', figsize=(10, 6), is_horizontal=False):
    """
    Cria um gráfico de barras.

    Args:
        data: DataFrame ou Series com os dados
        x: Nome da coluna para o eixo X
        y: Nome da coluna para o eixo Y
        title: Título do gráfico
        xlabel: Rótulo do eixo X (opcional)
        ylabel: Rótulo do eixo Y (opcional)
        color: Cor das barras
        figsize: Tamanho da figura
        is_horizontal: Se True, o gráfico será de barras horizontais.

    Returns:
        fig, ax: Figura e eixos do matplotlib
    """
    fig, ax = plt.subplots(figsize=figsize)

    if is_horizontal:
        bars = sns.barplot(data=data, x=x, y=y, color=color, ax=ax)
        for bar in bars.patches:
            width = bar.get_width()
            ax.text(
                width,
                bar.get_y() + bar.get_height() / 2,
                f'{int(width):,}',
                ha='left',
                va='center'
            )
    else:
        bars = sns.barplot(data=data, x=x, y=y, color=color, ax=ax)
        for bar in bars.patches:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f'{int(height):,}',
                ha='center',
                va='bottom'
            )

    ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)

    plt.tight_layout()
    return fig, ax


def plot_pie_chart(data, labels, title, figsize=(8, 8)):
    """
    Cria um gráfico de pizza.

    Args:
        data: Lista ou array com os valores
        labels: Lista de rótulos
        title: Título do gráfico
        figsize: Tamanho da figura

    Returns:
        fig, ax: Figura e eixos do matplotlib
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.pie(
        data,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Pastel1(np.linspace(0, 1, len(data)))
    )
    ax.set_title(title)
    ax.axis('equal')  # garante círculo perfeito

    plt.tight_layout()
    return fig, ax


def plot_histogram(data, bins=None, title=None,
                  xlabel=None, ylabel=None,
                  color='navy', figsize=(10, 6)):
    """
    Cria um histograma.

    Args:
        data: Série ou array com os dados
        bins: Número de bins ou lista de bins
        title: Título do gráfico
        xlabel: Rótulo do eixo X
        ylabel: Rótulo do eixo Y
        color: Cor do histograma
        figsize: Tamanho da figura

    Returns:
        fig, ax: Figura e eixos do matplotlib
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.histplot(data, bins=bins, kde=False, color=color, ax=ax)

    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)

    plt.tight_layout()
    return fig, ax

def plot_scatter_chart(data, x, y, c, cmap, s, alpha, title, xlabel, ylabel, figsize=(10, 6)):
    """
    Cria um gráfico de dispersão.
    """
    fig, ax = plt.subplots(figsize=figsize)
    scatter = ax.scatter(x=data[x], y=data[y], c=data[c], cmap=cmap, s=s, alpha=alpha)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.colorbar(scatter, label=c)
    plt.tight_layout()
    return fig, ax
