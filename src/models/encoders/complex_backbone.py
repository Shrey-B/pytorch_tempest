from efficientnet_pytorch import EfficientNet
from torch import nn


class BackboneModeI(nn.Module):
    """
    By phalanx @ZFPhalanx

    """
    def __init__(self, backbone_name: str, pretrain: bool = True, advdrop: bool = False):
        super().__init__()
        self.backbone_name = backbone_name
        self.encoder = nn.ModuleList()
        self.model = None

        if 'resnext' in backbone_name or 'resnet' in backbone_name or backbone_name.startswith('resnest'):
            if backbone_name.startswith('se'):
                pretrain = 'imagenet' if pretrain else None
            model = eval(backbone_name)(pretrain=pretrain)
            if backbone_name.startswith('se'):
                self.encoder.append(nn.Sequential(model.layer0, model.layer1))
            else:
                self.encoder.append(nn.Sequential(*(list(model.children())[:4]), model.layer1))

            self.encoder.append(model.layer2)
            self.encoder.append(model.layer3)
            self.encoder.append(model.layer4)

        elif backbone_name.startswith('densenet'):
            model = eval(backbone_name)(pretrain=pretrain).features
            transition1 = list(model.transition1.children())
            transition2 = list(model.transition2.children())
            transition3 = list(model.transition3.children())
            self.encoder.append(nn.Sequential(*(list(model.children())[:4]), model.denseblock1, *transition1[:2]))
            self.encoder.append(nn.Sequential(*transition1[2:], model.denseblock2, *transition2[:2]))
            self.encoder.append(nn.Sequential(*transition2[2:], model.denseblock3, *transition3[:2]))
            self.encoder.append(nn.Sequential(*transition3[2:], model.denseblock4, nn.ReLU(True)))

        elif backbone_name.startswith('efficientnet'):
            if pretrain:
                self.model = EfficientNet.from_pretrained(backbone_name, advprop=advdrop)
            else:
                self.model = EfficientNet.from_pretrained(backbone_name)
            # self.indexes = EFFICIENT_BLOCK_INDEXES(backbone_name)
            del self.model._avg_pooling, self.model._dropout, self.model._fc

    def forward(self, x):
        outputs = []
        if 'efficientnet' in self.backbone_name:
            x = self.model._swish(self.model._bn0(self.model._conv_stem(x)))
            for idx, block in enumerate(self.model._blocks):
                drop_connect_rate = self.model._global_params.drop_connect_rate
                if drop_connect_rate:
                    drop_connect_rate *= float(idx) / len(self.model._blocks)
                x = block(x, drop_connect_rate=drop_connect_rate)
                # TODO use indexes[0] for high resolution image
                # if idx in self.indexes[1:]:
                if idx > 1:
                    outputs.append(x)
            x = self.model._swish(self.model._bn1(self.model._conv_head(x)))
            outputs.append(x)
        else:
            for e in self.encoder:
                x = e(x)
                outputs.append(x)
        return outputs