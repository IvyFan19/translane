import torch
import torch.nn as nn

from .py_utils import kp, AELoss
from configuration import setup_configurations

def conv3x3(in_planes, out_planes, stride=1, groups=1, dilation=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=dilation, groups=groups, bias=False, dilation=dilation)

def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None):
        super(BasicBlock, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        if groups != 1 or base_width != 64:
            raise ValueError('BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError("Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = norm_layer(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = norm_layer(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out

class Bottleneck(nn.Module):
    # Bottleneck in torchvision places the stride for downsampling at 3x3 convolution(self.conv2)
    # while original implementation places the stride at the first 1x1 convolution(self.conv1)
    # according to "Deep residual learning for image recognition"https://arxiv.org/abs/1512.03385.
    # This variant is also known as ResNet V1.5 and improves accuracy according to
    # https://ngc.nvidia.com/catalog/model-scripts/nvidia:resnet_50_v1_5_for_pytorch.

    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None):
        super(Bottleneck, self).__init__()
        if norm_layer is None:
            norm_layer = nn.BatchNorm2d
        width = int(planes * (base_width / 64.)) * groups
        # Both self.conv2 and self.downsample layers downsample the input when stride != 1
        self.conv1 = conv1x1(inplanes, width)
        self.bn1 = norm_layer(width)
        self.conv2 = conv3x3(width, width, stride, groups, dilation)
        self.bn2 = norm_layer(width)
        self.conv3 = conv1x1(width, planes * self.expansion)
        self.bn3 = norm_layer(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out

class model(kp):
    def __init__(self, flag=False):
        """
        res18  BasicBlock [2, 2, 2, 2]
        res34  BasicBlock [3, 4, 6, 3]
        res50  Bottleneck [3, 4, 6, 3]
        res101 Bottleneck [3, 4, 23, 3]
        res152 Bottleneck [3, 8, 36, 3]
        """

        layers          = setup_configurations.res_layers
        res_dims        = setup_configurations.res_dims
        res_strides     = setup_configurations.res_strides
        attn_dim        = setup_configurations.attn_dim
        dim_feedforward = setup_configurations.dim_feedforward

        num_queries = setup_configurations.num_queries  # number of joints
        drop_out    = setup_configurations.drop_out
        num_heads   = setup_configurations.num_heads
        enc_layers  = setup_configurations.enc_layers
        dec_layers  = setup_configurations.dec_layers
        lsp_dim     = setup_configurations.lsp_dim
        mlp_layers  = setup_configurations.mlp_layers
        lane_cls     = setup_configurations.lane_categories

        aux_loss = setup_configurations.aux_loss
        pos_type = setup_configurations.pos_type
        pre_norm = setup_configurations.pre_norm
        return_intermediate = setup_configurations.return_intermediate

        if setup_configurations.block == 'BasicBlock':
            block = BasicBlock
        elif setup_configurations.block == 'BottleNeck':
            block = Bottleneck
        else:
            raise ValueError('invalid setup_configurations.block: {}'.format(setup_configurations.block))

        super(model, self).__init__(
            flag=flag,
            block=block,
            layers=layers,
            res_dims=res_dims,
            res_strides=res_strides,
            attn_dim=attn_dim,
            num_queries=num_queries,
            aux_loss=aux_loss,
            pos_type=pos_type,
            drop_out=drop_out,
            num_heads=num_heads,
            dim_feedforward=dim_feedforward,
            enc_layers=enc_layers,
            dec_layers=dec_layers,
            pre_norm=pre_norm,
            return_intermediate=return_intermediate,
            num_cls=lane_cls,
            lsp_dim=lsp_dim,
            mlp_layers=mlp_layers
        )

class loss(AELoss):
    def __init__(self):
        super(loss, self).__init__(
            debug_path=setup_configurations.result_dir,
            aux_loss=setup_configurations.aux_loss,
            num_classes=setup_configurations.lane_categories,
            dec_layers=setup_configurations.dec_layers
        )
