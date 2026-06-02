import torch
import torch.nn as nn


class MLPAttentionHead(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        attention_hidden_dim: int = 128,
        classifier_hidden_dim: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.pool_attention = nn.Sequential(
            nn.Linear(hidden_size, attention_hidden_dim),
            nn.Tanh(),
            nn.Linear(attention_hidden_dim, 1),
        )

        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, classifier_hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden_dim, 1),
        )

    def forward(
        self,
        token_hidden: torch.Tensor,
        attention_mask: torch.Tensor,
        return_attention: bool = False,
    ):
        attn_scores = self.pool_attention(token_hidden).squeeze(-1)
        attn_scores = attn_scores.masked_fill(attention_mask == 0, -1e9)

        attn_weights = torch.softmax(attn_scores, dim=-1)

        pooled = torch.sum(
            token_hidden * attn_weights.unsqueeze(-1),
            dim=1,
        )

        logits = self.classifier(pooled).squeeze(-1)

        if return_attention:
            return logits, attn_weights

        return logits